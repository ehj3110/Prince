"""Support separator module for Graphite geometry pipeline.

Decouples combined multi-shell STL files containing printed parts and slicer-generated
supports into co-registered Trimesh objects, and tags contact tip regions.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.spatial import cKDTree
import trimesh
from trimesh.proximity import _corresponding

logger = logging.getLogger(__name__)


def _ensure_trimesh(obj: Union[str, Path, trimesh.Trimesh, trimesh.Scene]) -> trimesh.Trimesh:
    """Load or convert an input object into a trimesh.Trimesh instance.
    
    Args:
        obj: File path, Path object, Trimesh, or Scene.

    Returns:
        trimesh.Trimesh instance.
    """
    if isinstance(obj, (str, Path)):
        path = Path(obj).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Mesh file not found: {path}")
        loaded = trimesh.load(str(path), force="mesh")
        if isinstance(loaded, trimesh.Scene):
            if len(loaded.geometry) == 0:
                return trimesh.Trimesh()
            return trimesh.util.concatenate(list(loaded.geometry.values()))
        return loaded
    elif isinstance(obj, trimesh.Scene):
        if len(obj.geometry) == 0:
            return trimesh.Trimesh()
        return trimesh.util.concatenate(list(obj.geometry.values()))
    elif isinstance(obj, trimesh.Trimesh):
        return obj
    else:
        raise TypeError(f"Expected file path, Path, or trimesh.Trimesh, got {type(obj)}")


def compute_mesh_surface_distances(
    mesh: trimesh.Trimesh,
    query_points: np.ndarray,
    candidate_distance_multiplier: float = 2.0,
    max_candidates_distance: Optional[float] = None,
    num_samples: int = 15000,
) -> np.ndarray:
    """Compute distances from query points to the surface of a mesh.
    
    Uses a hybrid approach combining spatial KDTree query over surface points,
    face centroids, and vertices, followed by exact point-to-triangle projections
    using trimesh's proximity solver for nearby candidates.
    
    Args:
        mesh: Target geometry mesh.
        query_points: (N, 3) float array of 3D query points.
        candidate_distance_multiplier: Multiplier for candidate search radius.
        max_candidates_distance: If set, only refine points whose initial KDTree distance
            is <= max_candidates_distance.
        num_samples: Number of surface sample points to generate for KDTree coverage.

    Returns:
        (N,) float array of shortest distances from each query point to mesh surface.
    """
    query_points = np.asanyarray(query_points, dtype=np.float64)
    if len(query_points) == 0:
        return np.empty((0,), dtype=np.float64)
    if mesh is None or len(mesh.vertices) == 0:
        return np.full(len(query_points), np.inf, dtype=np.float64)

    # If mesh has no faces, compute distance to vertices directly
    if len(mesh.faces) == 0:
        tree = cKDTree(mesh.vertices)
        dists, _ = tree.query(query_points)
        return dists

    # Build dense representative surface points for KDTree broadphase
    pts_list = [mesh.vertices]
    face_indices_list = [
        np.array([mesh.vertex_faces[i][0] if len(mesh.vertex_faces[i]) > 0 else 0 
                  for i in range(len(mesh.vertices))], dtype=np.int64)
    ]

    if hasattr(mesh, "triangles_center") and len(mesh.triangles_center) > 0:
        pts_list.append(mesh.triangles_center)
        face_indices_list.append(np.arange(len(mesh.faces), dtype=np.int64))

    # Surface sampling for broad planar/large triangles
    if mesh.area > 1e-6 and num_samples > 0:
        try:
            samples, sampled_faces = trimesh.sample.sample_surface(mesh, num_samples)
            pts_list.append(samples)
            face_indices_list.append(sampled_faces)
        except Exception as e:
            logger.debug("Surface sampling fallback: %s", e)

    all_pts = np.vstack(pts_list)
    all_face_idx = np.hstack(face_indices_list)

    tree = cKDTree(all_pts)
    approx_dists, nearest_indices = tree.query(query_points, k=min(6, len(all_pts)))

    if approx_dists.ndim == 1:
        approx_d = approx_dists
        k_indices = nearest_indices[:, None]
    else:
        approx_d = approx_dists[:, 0]
        k_indices = nearest_indices

    exact_dists = approx_d.copy()

    # Determine which points need exact triangle refinement
    if max_candidates_distance is not None:
        refine_mask = approx_d <= max_candidates_distance
    else:
        refine_mask = np.ones(len(query_points), dtype=bool)

    if not np.any(refine_mask):
        return exact_dists

    refine_indices = np.where(refine_mask)[0]
    
    # Gather candidate triangles for the query points requiring refinement
    cand_tri_list: List[np.ndarray] = []
    cand_pt_list: List[np.ndarray] = []
    cand_point_idx: List[int] = []

    mesh_triangles = mesh.triangles
    for p_idx in refine_indices:
        p = query_points[p_idx]
        associated_faces = np.unique(all_face_idx[k_indices[p_idx]])
        for f_idx in associated_faces:
            cand_tri_list.append(mesh_triangles[f_idx])
            cand_pt_list.append(p)
            cand_point_idx.append(p_idx)

    if cand_tri_list:
        cand_tris_arr = np.array(cand_tri_list, dtype=np.float64)
        cand_pts_arr = np.array(cand_pt_list, dtype=np.float64)
        
        # Calculate exact closest points on candidate triangles
        proj_pts = _corresponding(cand_tris_arr, cand_pts_arr)
        proj_dists = np.linalg.norm(proj_pts - cand_pts_arr, axis=1)

        for p_idx, dist in zip(cand_point_idx, proj_dists):
            if dist < exact_dists[p_idx]:
                exact_dists[p_idx] = dist

    return exact_dists


def extract_support_tips(
    part_mesh: trimesh.Trimesh,
    support_mesh: trimesh.Trimesh,
    tip_distance_threshold: float = 0.8,
    g_pillar: int = 255,
    g_tip: int = 128,
) -> Dict[str, Union[np.ndarray, Optional[trimesh.Trimesh]]]:
    """Identifies vertices and faces on `support_mesh` that lie within `tip_distance_threshold` (mm) of `part_mesh`.

    Downstream DLP projection mask compilation tags contact tip regions with lower
    grayscale intensity than bulk pillars to prevent overcuring and facilitate release.

    Args:
        part_mesh: The printed part geometry.
        support_mesh: The support structure mesh.
        tip_distance_threshold: Distance in mm within which a support vertex is
            classified as a contact tip. Defaults to 0.8 mm.
        g_pillar: Grayscale intensity [0-255] for bulk support pillars. Defaults to 255.
        g_tip: Grayscale intensity [0-255] for contact tips. Defaults to 128.

    Returns:
        dict containing:
            - 'tip_vertex_indices': np.ndarray of vertex indices on support_mesh
            - 'tip_submesh': Optional trimesh.Trimesh of just the tip elements
            - 'support_mesh_with_vertex_colors': trimesh.Trimesh where bulk supports
              are tagged with intensity G_pillar and tips are tagged with G_tip.
    """
    if support_mesh is None or len(support_mesh.vertices) == 0:
        empty_mesh = trimesh.Trimesh()
        return {
            "tip_vertex_indices": np.empty(0, dtype=np.int64),
            "tip_submesh": empty_mesh,
            "support_mesh_with_vertex_colors": empty_mesh,
        }

    if part_mesh is None or len(part_mesh.vertices) == 0:
        # No part provided: all support is bulk pillar
        bulk_colors = np.full((len(support_mesh.vertices), 4), [g_pillar, g_pillar, g_pillar, 255], dtype=np.uint8)
        colored_mesh = support_mesh.copy()
        colored_mesh.visual.vertex_colors = bulk_colors
        return {
            "tip_vertex_indices": np.empty(0, dtype=np.int64),
            "tip_submesh": trimesh.Trimesh(),
            "support_mesh_with_vertex_colors": colored_mesh,
        }

    # Calculate exact distance from each support vertex to the part mesh surface
    distances = compute_mesh_surface_distances(
        mesh=part_mesh,
        query_points=support_mesh.vertices,
        max_candidates_distance=tip_distance_threshold + 0.5,
    )

    tip_mask = distances <= tip_distance_threshold
    tip_vertex_indices = np.where(tip_mask)[0]

    # Extract tip submesh
    tip_submesh: Optional[trimesh.Trimesh] = None
    if len(tip_vertex_indices) > 0 and len(support_mesh.faces) > 0:
        # Faces where all vertices are within the tip distance threshold
        all_tip_faces = np.all(np.isin(support_mesh.faces, tip_vertex_indices), axis=1)
        if np.any(all_tip_faces):
            tip_submesh = support_mesh.submesh([all_tip_faces], append=True)
        else:
            # Fall back to faces where any vertex is within threshold
            any_tip_faces = np.any(np.isin(support_mesh.faces, tip_vertex_indices), axis=1)
            if np.any(any_tip_faces):
                tip_submesh = support_mesh.submesh([any_tip_faces], append=True)

    if tip_submesh is None:
        tip_submesh = trimesh.Trimesh(
            vertices=np.empty((0, 3), dtype=np.float64),
            faces=np.empty((0, 3), dtype=np.int64),
        )

    # Create colored support mesh
    colored_mesh = support_mesh.copy()
    vertex_colors = np.full(
        (len(support_mesh.vertices), 4),
        [g_pillar, g_pillar, g_pillar, 255],
        dtype=np.uint8,
    )
    if len(tip_vertex_indices) > 0:
        vertex_colors[tip_vertex_indices] = [g_tip, g_tip, g_tip, 255]

    colored_mesh.visual.vertex_colors = vertex_colors
    colored_mesh.vertex_attributes["is_tip"] = tip_mask
    colored_mesh.vertex_attributes["grayscale_intensity"] = vertex_colors[:, 0]

    return {
        "tip_vertex_indices": tip_vertex_indices,
        "tip_submesh": tip_submesh,
        "support_mesh_with_vertex_colors": colored_mesh,
    }


def detect_and_disconnect_support_tops(
    support_mesh: trimesh.Trimesh,
    part_mesh: Optional[trimesh.Trimesh] = None,
    mode: str = "auto",
    top_height_mm: float = 1.5,
    xy_cluster_radius: float = 2.0,
    contact_distance_threshold: float = 2.5,
) -> Tuple[trimesh.Trimesh, trimesh.Trimesh, List[Dict[str, Any]]]:
    """Detects the tops of each support pillar and cleanly disconnects them from bulk supports.

    Unlike Euclidean distance thresholding which cuts across arbitrary triangles and leaves
    fragmented, jagged shards, this function:
    1. Clusters support geometry into distinct pillar columns based on XY footprint.
    2. Identifies the peak/head of each support pillar contacting or penetrating the part.
    3. Disconnects the tops cleanly:
       - 'component' mode: Identifies the intact, complete top modular component/shell
         for each pillar (zero triangle loss, 100% geometry preservation).
       - 'planar_cut' mode: Performs a clean cross-sectional planar cut at `top_height_mm`
         below each detected peak.
       - 'auto' mode: Automatically uses 'component' if multi-shell support geometry is
         present, or 'planar_cut' for monolithic single-shell meshes.

    Args:
        support_mesh: The support structure mesh.
        part_mesh: Optional printed part geometry for contact validation.
        mode: Strategy ('auto', 'component', or 'planar_cut').
        top_height_mm: Cut depth (mm) below detected peak when using planar_cut.
        xy_cluster_radius: Spatial clustering radius (mm) in XY plane to group pillar shells.
        contact_distance_threshold: Maximum distance to part surface for contact validation.

    Returns:
        Tuple of:
            - bulk_supports: trimesh.Trimesh of the trunks, rafts, and scaffolding.
            - disconnected_tops: trimesh.Trimesh of the cleanly separated support tops.
            - pillar_info: List of dicts describing each detected pillar.
    """
    if support_mesh is None or len(support_mesh.vertices) == 0:
        return trimesh.Trimesh(), trimesh.Trimesh(), []

    shells: List[trimesh.Trimesh] = trimesh.graph.split(support_mesh, only_watertight=False, repair=False)

    chosen_mode = mode
    if chosen_mode == "auto":
        chosen_mode = "component" if len(shells) > 1 else "planar_cut"

    pillar_info: List[Dict[str, Any]] = []

    if chosen_mode == "component" and len(shells) > 1:
        # Calculate bounding box centers in XY (safe from open/degenerate shell center_mass issues)
        centers = np.array([(s.bounds[0][:2] + s.bounds[1][:2]) / 2.0 for s in shells])

        # Cluster shells by XY proximity
        pillar_clusters: List[List[int]] = []
        cluster_centers: List[np.ndarray] = []
        for i, c in enumerate(centers):
            matched = False
            for p_idx, p_c in enumerate(cluster_centers):
                if np.linalg.norm(c - p_c) < xy_cluster_radius:
                    pillar_clusters[p_idx].append(i)
                    cluster_centers[p_idx] = np.mean([centers[k] for k in pillar_clusters[p_idx]], axis=0)
                    matched = True
                    break
            if not matched:
                pillar_clusters.append([i])
                cluster_centers.append(c.copy())

        try:
            from trimesh.intersections import slice_mesh_plane
            has_slice = True
        except Exception:
            has_slice = False

        top_elements: List[trimesh.Trimesh] = []
        bulk_elements: List[trimesh.Trimesh] = []

        for p_idx, s_indices in enumerate(pillar_clusters):
            p_z_max = max(shells[k].bounds[1, 2] for k in s_indices)

            # Check if this pillar is a base raft / footing well below the part
            if part_mesh is not None and len(part_mesh.vertices) > 0:
                if p_z_max < part_mesh.bounds[0, 2] - contact_distance_threshold:
                    for k in s_indices:
                        bulk_elements.append(shells[k])
                    continue
            elif p_z_max <= support_mesh.bounds[0, 2] + 2.5:
                # Raft at build plate
                for k in s_indices:
                    bulk_elements.append(shells[k])
                continue

            if len(s_indices) > 1:
                # Multi-shell pillar: find the top modular shell(s)
                peak_shells = []
                for k in s_indices:
                    s = shells[k]
                    if np.isclose(s.bounds[1, 2], p_z_max, atol=1e-2):
                        top_elements.append(s)
                        peak_shells.append(s)
                    else:
                        bulk_elements.append(s)

                top_faces = sum(len(s.faces) for s in peak_shells)
                pillar_info.append({
                    "pillar_id": p_idx,
                    "xy_center": cluster_centers[p_idx].tolist(),
                    "z_peak": float(p_z_max),
                    "top_shells_count": len(peak_shells),
                    "top_faces_count": top_faces,
                })
            else:
                # Monolithic single-shell pillar in multi-shell assembly
                s = shells[s_indices[0]]
                dz = s.bounds[1, 2] - s.bounds[0, 2]
                if dz > top_height_mm * 1.5 and has_slice:
                    cut_z = p_z_max - top_height_mm
                    top = slice_mesh_plane(s, plane_normal=[0, 0, 1], plane_origin=[0, 0, cut_z])
                    bulk = slice_mesh_plane(s, plane_normal=[0, 0, -1], plane_origin=[0, 0, cut_z])
                    top_elements.append(top)
                    bulk_elements.append(bulk)
                    pillar_info.append({
                        "pillar_id": p_idx,
                        "xy_center": cluster_centers[p_idx].tolist(),
                        "z_peak": float(p_z_max),
                        "top_faces_count": len(top.faces),
                    })
                else:
                    top_elements.append(s)
                    pillar_info.append({
                        "pillar_id": p_idx,
                        "xy_center": cluster_centers[p_idx].tolist(),
                        "z_peak": float(p_z_max),
                        "top_faces_count": len(s.faces),
                    })

        disconnected_tops = trimesh.util.concatenate(top_elements) if top_elements else trimesh.Trimesh()
        bulk_supports = trimesh.util.concatenate(bulk_elements) if bulk_elements else trimesh.Trimesh()

        return bulk_supports, disconnected_tops, pillar_info

    else:
        # Planar cut mode: Clean horizontal cross-section cut below each detected pillar top
        try:
            from trimesh.intersections import slice_mesh_plane
            has_slice = True
        except Exception:
            has_slice = False

        if part_mesh is not None and len(part_mesh.vertices) > 0:
            dists = compute_mesh_surface_distances(
                mesh=part_mesh,
                query_points=support_mesh.vertices,
                max_candidates_distance=contact_distance_threshold,
            )
            top_mask = dists <= contact_distance_threshold
        else:
            z_threshold = support_mesh.bounds[1, 2] - top_height_mm
            top_mask = support_mesh.vertices[:, 2] >= z_threshold

        if not np.any(top_mask):
            return support_mesh.copy(), trimesh.Trimesh(), []

        z_peak = float(np.max(support_mesh.vertices[top_mask, 2]))
        cut_z = z_peak - top_height_mm

        pillar_info.append({
            "pillar_id": 0,
            "xy_center": [(support_mesh.bounds[0, 0] + support_mesh.bounds[1, 0]) / 2.0,
                          (support_mesh.bounds[0, 1] + support_mesh.bounds[1, 1]) / 2.0],
            "z_peak": z_peak,
            "cut_z": cut_z,
        })

        if has_slice:
            disconnected_tops = slice_mesh_plane(
                support_mesh, plane_normal=[0, 0, 1], plane_origin=[0, 0, cut_z]
            )
            bulk_supports = slice_mesh_plane(
                support_mesh, plane_normal=[0, 0, -1], plane_origin=[0, 0, cut_z]
            )
        else:
            face_centers = support_mesh.triangles_center
            is_top_face = face_centers[:, 2] >= cut_z
            disconnected_tops = support_mesh.submesh([is_top_face], append=True) if np.any(is_top_face) else trimesh.Trimesh()
            bulk_supports = support_mesh.submesh([~is_top_face], append=True) if np.any(~is_top_face) else trimesh.Trimesh()

        return bulk_supports, disconnected_tops, pillar_info


def _score_shell_heuristic(
    shell: trimesh.Trimesh,
    global_z_min: float,
    global_z_max: float,
    max_volume: float,
    max_area: float,
) -> float:
    """Score a shell's likelihood of being a support structure in [0.0, 1.0].
    
    Heuristic rules:
    - High aspect ratio in Z (slender columns, cones, trees) -> high support score.
    - Low transverse dimensions (radius < 2.5mm) -> high support score.
    - Low volume-to-area ratio (thin shell / branches) -> high support score.
    - Rafts: Located at global Z min with small Z thickness and broad XY -> high support score.
    - Primary bulk body: large volume, low aspect ratio -> low support score.
    """
    if len(shell.vertices) == 0:
        return 0.0

    bbox_min = np.min(shell.vertices, axis=0)
    bbox_max = np.max(shell.vertices, axis=0)
    extents = bbox_max - bbox_min
    dx, dy, dz = extents[0], extents[1], extents[2]

    d_xy_max = max(dx, dy, 1e-6)
    d_xy_min = min(dx, dy)
    aspect_ratio_z = dz / d_xy_max

    # Volume calculation
    vol = 0.0
    if len(shell.faces) >= 4 and shell.is_watertight:
        try:
            v_calc = float(shell.volume)
            if not np.isnan(v_calc) and v_calc > 0:
                vol = v_calc
        except Exception:
            vol = 0.0
    if vol == 0.0 and len(shell.vertices) >= 4 and np.min(extents) > 1e-4:
        try:
            vol = float(shell.convex_hull.volume)
            if np.isnan(vol):
                vol = 0.0
        except Exception:
            vol = 0.0

    area = max(shell.area, 1e-6)
    v_to_a = vol / area

    # Base raft detection: near bottom build plate, thin in Z, wide in XY
    z_bottom_offset = bbox_min[2] - global_z_min
    if z_bottom_offset < 0.2 and dz <= 2.5 and d_xy_max > 5.0 and aspect_ratio_z < 0.2:
        return 0.95

    # Slender vertical support pillars / tree branches
    if aspect_ratio_z >= 2.0 and d_xy_max < 5.0:
        return 0.90

    if aspect_ratio_z >= 1.5 and d_xy_max < 3.0:
        return 0.85

    # Thin cross section with low characteristic thickness
    if d_xy_max < 2.5 and dz > 2.0 and v_to_a < 0.6:
        return 0.80

    # Bulky primary body detection
    if vol >= 0.5 * max_volume and max_volume > 0:
        return 0.05

    if vol >= 0.2 * max_volume and v_to_a > 1.2:
        return 0.10

    # Ambiguous intermediate: evaluate relative volume and thickness
    score = 0.5
    if aspect_ratio_z > 1.2:
        score += 0.15
    if d_xy_max < 4.0:
        score += 0.15
    if v_to_a < 0.8:
        score += 0.10
    if vol < 0.05 * max_volume:
        score += 0.10

    return np.clip(score, 0.0, 1.0)


def split_supported_mesh(
    combined_mesh: Union[str, Path, trimesh.Trimesh],
    reference_mesh: Optional[Union[str, Path, trimesh.Trimesh]] = None,
    distance_threshold: float = 0.05,
    distance_metric: str = "median",
) -> Tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """Decouples combined multi-shell mesh into co-registered part and support meshes.

    Dual-path implementation:
    - Mode A (Reference Guided): When `reference_mesh` is provided, tests vertex
      proximity of each disjoint shell against the reference geometry.
    - Mode B (Autonomous / Heuristic): When no reference is provided, analyzes
      geometric features (aspect ratio, characteristic thickness, volume, rafts).

    Args:
        combined_mesh: The multi-shell STL containing both part and supports.
        reference_mesh: Optional original oriented part STL.
        distance_threshold: Distance threshold (mm) for Mode A classification.
            Defaults to 0.05 mm.
        distance_metric: Statistic for Mode A ('median' or 'mean'). Defaults to 'median'.

    Returns:
        Tuple of (part_mesh, support_mesh), both retaining exact world coordinates.
    """
    c_mesh = _ensure_trimesh(combined_mesh)
    if len(c_mesh.faces) == 0:
        return trimesh.Trimesh(), trimesh.Trimesh()

    # Split combined mesh into disjoint connected components
    shells: List[trimesh.Trimesh] = trimesh.graph.split(c_mesh, only_watertight=False, repair=False)
    if len(shells) == 0:
        return trimesh.Trimesh(), trimesh.Trimesh()
    if len(shells) == 1:
        # If there's only one shell, check if it matches reference or classify as part
        if reference_mesh is not None:
            r_mesh = _ensure_trimesh(reference_mesh)
            tree = cKDTree(r_mesh.vertices)
            dists, _ = tree.query(shells[0].vertices)
            stat = np.median(dists) if distance_metric == "median" else np.mean(dists)
            if stat <= distance_threshold:
                return shells[0], trimesh.Trimesh()
            else:
                return trimesh.Trimesh(), shells[0]
        return shells[0], trimesh.Trimesh()

    part_shells: List[trimesh.Trimesh] = []
    support_shells: List[trimesh.Trimesh] = []

    if reference_mesh is not None:
        # -------------------------------------------------------------
        # Mode A: Reference Guided (Primary / High Reliability)
        # -------------------------------------------------------------
        r_mesh = _ensure_trimesh(reference_mesh)
        if len(r_mesh.vertices) == 0:
            logger.warning("Reference mesh contains 0 vertices; falling back to heuristic Mode B.")
            return split_supported_mesh(c_mesh, reference_mesh=None)

        # Build KDTree from reference mesh vertices and triangle centers
        ref_pts = [r_mesh.vertices]
        if hasattr(r_mesh, "triangles_center") and len(r_mesh.triangles_center) > 0:
            ref_pts.append(r_mesh.triangles_center)
        ref_tree = cKDTree(np.vstack(ref_pts))

        for idx, shell in enumerate(shells):
            if len(shell.vertices) == 0:
                continue
            dists, _ = ref_tree.query(shell.vertices)
            stat_dist = np.median(dists) if distance_metric == "median" else np.mean(dists)

            if stat_dist <= distance_threshold:
                part_shells.append(shell)
            else:
                support_shells.append(shell)
    else:
        # -------------------------------------------------------------
        # Mode B: Autonomous / Heuristic (Fallback without Reference)
        # -------------------------------------------------------------
        global_z_min = float(np.min(c_mesh.vertices[:, 2]))
        global_z_max = float(np.max(c_mesh.vertices[:, 2]))

        shell_volumes: List[float] = []
        shell_areas: List[float] = []
        for s in shells:
            v = 0.0
            if len(s.faces) >= 4 and s.is_watertight:
                try:
                    v_calc = float(s.volume)
                    if not np.isnan(v_calc) and v_calc > 0:
                        v = v_calc
                except Exception:
                    v = 0.0
            s_ext = s.bounds[1] - s.bounds[0]
            if v == 0.0 and len(s.vertices) >= 4 and np.min(s_ext) > 1e-4:
                try:
                    v = float(s.convex_hull.volume)
                    if np.isnan(v):
                        v = 0.0
                except Exception:
                    v = 0.0
            shell_volumes.append(v)
            shell_areas.append(s.area)

        max_vol = max(shell_volumes) if shell_volumes else 0.0
        max_area = max(shell_areas) if shell_areas else 0.0

        for idx, shell in enumerate(shells):
            score = _score_shell_heuristic(
                shell=shell,
                global_z_min=global_z_min,
                global_z_max=global_z_max,
                max_volume=max_vol,
                max_area=max_area,
            )

            # Check for ambiguity
            if 0.35 <= score <= 0.65:
                logger.warning(
                    "Ambiguity detected in heuristic support classification for shell %d "
                    "(score=%.2f, vol=%.2f, area=%.2f). Falling back to volume/area ranking.",
                    idx,
                    score,
                    shell_volumes[idx],
                    shell_areas[idx],
                )
                # Volume/area ranking fallback: high volume/area shells belong to part
                is_part = shell_volumes[idx] >= 0.1 * max_vol if max_vol > 0 else True
            else:
                is_part = score < 0.5

            if is_part:
                part_shells.append(shell)
            else:
                support_shells.append(shell)

    # Concatenate matched shells back into unified part and support meshes
    part_mesh = trimesh.util.concatenate(part_shells) if part_shells else trimesh.Trimesh()
    support_mesh = trimesh.util.concatenate(support_shells) if support_shells else trimesh.Trimesh()

    # Verify zero triangle loss invariant
    total_split_faces = len(part_mesh.faces) + len(support_mesh.faces)
    if total_split_faces != len(c_mesh.faces):
        logger.error(
            "Triangle loss mismatch: combined has %d faces, split has %d faces.",
            len(c_mesh.faces),
            total_split_faces,
        )

    return part_mesh, support_mesh


class SupportedMeshSeparator:
    """Pipelines splitting of supported STL files into part and supports, and tags contact tips."""

    def __init__(
        self,
        combined_path: Union[str, Path, trimesh.Trimesh],
        reference_part_path: Optional[Union[str, Path, trimesh.Trimesh]] = None,
    ) -> None:
        """Initialize SupportedMeshSeparator.

        Args:
            combined_path: Path to combined multi-shell STL or loaded Trimesh.
            reference_part_path: Optional path to reference original part STL or loaded Trimesh.
        """
        self.combined_path = combined_path
        self.reference_part_path = reference_part_path

        self.combined_mesh: trimesh.Trimesh = _ensure_trimesh(combined_path)
        self.reference_mesh: Optional[trimesh.Trimesh] = (
            _ensure_trimesh(reference_part_path) if reference_part_path is not None else None
        )

        self.part_mesh: Optional[trimesh.Trimesh] = None
        self.support_mesh: Optional[trimesh.Trimesh] = None
        self.tip_data: Optional[Dict[str, Union[np.ndarray, Optional[trimesh.Trimesh]]]] = None
        self.tip_submesh: Optional[trimesh.Trimesh] = None
        self.bulk_supports: Optional[trimesh.Trimesh] = None
        self.disconnected_tops: Optional[trimesh.Trimesh] = None
        self.pillar_info: Optional[List[Dict[str, Any]]] = None

    def separate(
        self,
        distance_threshold: float = 0.05,
        distance_metric: str = "median",
    ) -> Tuple[trimesh.Trimesh, trimesh.Trimesh]:
        """Separates the combined mesh into part and support meshes.

        Args:
            distance_threshold: Distance threshold (mm) for reference guided mode.
            distance_metric: Distance aggregation metric ('median' or 'mean').

        Returns:
            Tuple of (part_mesh, support_mesh) retaining exact global coordinates.
        """
        self.part_mesh, self.support_mesh = split_supported_mesh(
            combined_mesh=self.combined_mesh,
            reference_mesh=self.reference_mesh,
            distance_threshold=distance_threshold,
            distance_metric=distance_metric,
        )
        return self.part_mesh, self.support_mesh

    def tag_tips(
        self,
        threshold_mm: float = 0.8,
        g_pillar: int = 255,
        g_tip: int = 128,
    ) -> trimesh.Trimesh:
        """Identifies contact tips and returns the support mesh with vertex colors/attributes.

        Args:
            threshold_mm: Distance threshold (mm) within which support elements are tagged as tips.
            g_pillar: Grayscale intensity for bulk supports.
            g_tip: Grayscale intensity for contact tips.

        Returns:
            trimesh.Trimesh of supports with vertex attributes and visual colors applied.
        """
        if self.part_mesh is None or self.support_mesh is None:
            self.separate()

        self.tip_data = extract_support_tips(
            part_mesh=self.part_mesh,
            support_mesh=self.support_mesh,
            tip_distance_threshold=threshold_mm,
            g_pillar=g_pillar,
            g_tip=g_tip,
        )
        self.tip_submesh = self.tip_data.get("tip_submesh")
        colored_support = self.tip_data["support_mesh_with_vertex_colors"]
        assert isinstance(colored_support, trimesh.Trimesh)
        return colored_support

    def disconnect_tops(
        self,
        mode: str = "auto",
        top_height_mm: float = 1.5,
        xy_cluster_radius: float = 2.0,
        contact_distance_threshold: float = 2.5,
    ) -> Tuple[trimesh.Trimesh, trimesh.Trimesh]:
        """Detects tops of each support pillar and cleanly disconnects them from bulk supports.

        Args:
            mode: 'auto', 'component', or 'planar_cut'.
            top_height_mm: Cut depth below detected peak when using planar_cut.
            xy_cluster_radius: Clustering radius in XY to group pillar shells.
            contact_distance_threshold: Distance tolerance for part contact validation.

        Returns:
            Tuple of (bulk_supports, disconnected_tops).
        """
        if self.part_mesh is None or self.support_mesh is None:
            self.separate()

        self.bulk_supports, self.disconnected_tops, self.pillar_info = detect_and_disconnect_support_tops(
            support_mesh=self.support_mesh,
            part_mesh=self.part_mesh,
            mode=mode,
            top_height_mm=top_height_mm,
            xy_cluster_radius=xy_cluster_radius,
            contact_distance_threshold=contact_distance_threshold,
        )
        self.tip_submesh = self.disconnected_tops
        return self.bulk_supports, self.disconnected_tops

    def export(
        self,
        output_dir: Union[str, Path],
        prefix: str = "",
        export_tips: bool = True,
    ) -> Dict[str, str]:
        """Saves part.stl, supports.stl, and optionally tips.stl/bulk_supports.stl retaining exact world coordinates.

        Args:
            output_dir: Directory where STLs will be saved.
            prefix: Optional filename prefix.
            export_tips: Whether to export tips.stl if tips or disconnected tops are available.

        Returns:
            Dict mapping key ('part', 'supports', 'tips', 'tops', 'bulk_supports') to saved file paths.
        """
        if self.part_mesh is None or self.support_mesh is None:
            self.separate()

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        exported_files: Dict[str, str] = {}

        # Save part.stl
        part_file = out_path / f"{prefix}part.stl"
        self.part_mesh.export(str(part_file))
        exported_files["part"] = str(part_file)

        # Save supports.stl
        supports_file = out_path / f"{prefix}supports.stl"
        self.support_mesh.export(str(supports_file))
        exported_files["supports"] = str(supports_file)

        # Save bulk_supports.stl if disconnected_tops was computed
        if self.bulk_supports is not None and len(self.bulk_supports.faces) > 0:
            bulk_file = out_path / f"{prefix}bulk_supports.stl"
            self.bulk_supports.export(str(bulk_file))
            exported_files["bulk_supports"] = str(bulk_file)

        # Save tips.stl / tops.stl if requested and present
        if export_tips and self.tip_submesh is not None and len(self.tip_submesh.faces) > 0:
            tips_file = out_path / f"{prefix}tips.stl"
            self.tip_submesh.export(str(tips_file))
            exported_files["tips"] = str(tips_file)

            if self.disconnected_tops is not None and len(self.disconnected_tops.faces) > 0:
                tops_file = out_path / f"{prefix}tops.stl"
                self.disconnected_tops.export(str(tops_file))
                exported_files["tops"] = str(tops_file)

        return exported_files


def main() -> None:
    """CLI entrypoint for splitting supported STL into part and supports."""
    parser = argparse.ArgumentParser(
        description="Split combined supported STL into co-registered part and support meshes."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to combined multi-shell STL containing part and supports.",
    )
    parser.add_argument(
        "--ref",
        "-r",
        type=str,
        default=None,
        help="Path to reference original oriented part STL (Mode A).",
    )
    parser.add_argument(
        "--out-dir",
        "-o",
        type=str,
        default="./separated_meshes/",
        help="Directory to save separated output meshes (default: ./separated_meshes/).",
    )
    parser.add_argument(
        "--tip-threshold",
        "-t",
        type=float,
        default=0.8,
        help="Proximity threshold (mm) for support tip tagging (default: 0.8 mm).",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Prefix for exported output filenames (default: empty).",
    )
    parser.add_argument(
        "--distance-threshold",
        type=float,
        default=0.05,
        help="Surface distance tolerance (mm) for reference guided Mode A (default: 0.05 mm).",
    )
    parser.add_argument(
        "--disconnect-tops",
        action="store_true",
        help="Detect each pillar top and cleanly disconnect them from bulk supports.",
    )
    parser.add_argument(
        "--tops-mode",
        type=str,
        default="auto",
        choices=["auto", "component", "planar_cut"],
        help="Top disconnection mode: 'auto', 'component', or 'planar_cut' (default: auto).",
    )
    parser.add_argument(
        "--top-height",
        type=float,
        default=1.5,
        help="Cut depth (mm) below detected peak when using planar_cut (default: 1.5 mm).",
    )
    parser.add_argument(
        "--cluster-radius",
        type=float,
        default=2.0,
        help="Spatial clustering radius (mm) in XY plane to group pillar shells (default: 2.0 mm).",
    )
    parser.add_argument(
        "--no-tips",
        action="store_true",
        help="Disable tip tagging and tips.stl export.",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("Initializing SupportedMeshSeparator...")
    logger.info("Input mesh: %s", args.input)
    if args.ref:
        logger.info("Reference part mesh: %s (Mode A: Reference Guided)", args.ref)
    else:
        logger.info("No reference part provided (Mode B: Autonomous / Heuristic)")

    separator = SupportedMeshSeparator(
        combined_path=args.input,
        reference_part_path=args.ref,
    )

    logger.info("Splitting supported mesh into part and supports...")
    part_mesh, support_mesh = separator.separate(distance_threshold=args.distance_threshold)
    logger.info(
        "Separation complete: Part faces = %d, Support faces = %d (Total = %d)",
        len(part_mesh.faces),
        len(support_mesh.faces),
        len(part_mesh.faces) + len(support_mesh.faces),
    )

    if args.disconnect_tops:
        logger.info("Detecting support pillar tops and cleanly disconnecting them...")
        bulk_supp, tops = separator.disconnect_tops(
            mode=args.tops_mode,
            top_height_mm=args.top_height,
            xy_cluster_radius=args.cluster_radius,
        )
        logger.info(
            "Disconnected %d pillar tops (%d faces). Bulk supports have %d faces.",
            len(separator.pillar_info) if separator.pillar_info else 0,
            len(tops.faces),
            len(bulk_supp.faces),
        )
    elif not args.no_tips:
        logger.info("Tagging support contact tips (threshold = %.2f mm)...", args.tip_threshold)
        separator.tag_tips(threshold_mm=args.tip_threshold)
        if separator.tip_submesh is not None:
            logger.info("Identified %d tip faces.", len(separator.tip_submesh.faces))

    logger.info("Exporting separated meshes to %s...", args.out_dir)
    results = separator.export(
        output_dir=args.out_dir,
        prefix=args.prefix,
        export_tips=not args.no_tips or args.disconnect_tops,
    )
    for name, path in results.items():
        logger.info("Saved %s: %s", name, path)
    logger.info("Process completed successfully.")


if __name__ == "__main__":
    main()
