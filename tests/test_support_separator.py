"""Unit tests for Graphite support separator pipeline.

Tests synthetic cases (cube + penetrating cylinders, multi-shell parts, base rafts),
coordinate invariance, zero triangle loss, tip proximity tagging, and CLI execution.
Compatible with both pytest and unittest.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Tuple
import unittest

# Ensure repo root is on sys.path
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
import trimesh

from graphite.slicing.support_separator import (
    SupportedMeshSeparator,
    extract_support_tips,
    split_supported_mesh,
    detect_and_disconnect_support_tops,
)


def create_synthetic_supported_cube(
    cube_size: float = 20.0,
    pillar_radius: float = 0.6,
    pillar_height: float = 12.0,
    penetration: float = 0.3,
    with_raft: bool = False,
) -> Tuple[trimesh.Trimesh, trimesh.Trimesh, trimesh.Trimesh]:
    """Helper creating a synthetic part (cube) and penetrating support pillars.

    Part is placed with bottom face at Z = 10.0.
    Pillars are slender cylinders starting below Z = 10.0 and penetrating up to
    Z = 10.0 + penetration.

    Returns:
        (reference_cube, true_support_mesh, combined_mesh)
    """
    # Create cube: bounds [-10, 10] in X, Y; [10, 30] in Z
    cube = trimesh.creation.box(extents=(cube_size, cube_size, cube_size))
    cube.apply_translation([0.0, 0.0, 10.0 + cube_size / 2.0])

    pillars = []
    # 4 corner support pillars
    pillar_z_center = 10.0 + penetration - (pillar_height / 2.0)
    corner_offsets = [
        (-cube_size * 0.35, -cube_size * 0.35),
        (cube_size * 0.35, -cube_size * 0.35),
        (-cube_size * 0.35, cube_size * 0.35),
        (cube_size * 0.35, cube_size * 0.35),
    ]

    for ox, oy in corner_offsets:
        cyl = trimesh.creation.cylinder(radius=pillar_radius, height=pillar_height, sections=16)
        cyl.apply_translation([ox, oy, pillar_z_center])
        pillars.append(cyl)

    if with_raft:
        # Base raft at bottom of pillars: Z extent = 1.0 mm
        raft_z_center = 10.0 + penetration - pillar_height - 0.5
        raft = trimesh.creation.box(extents=(cube_size * 1.5, cube_size * 1.5, 1.0))
        raft.apply_translation([0.0, 0.0, raft_z_center])
        pillars.append(raft)

    supports = trimesh.util.concatenate(pillars)
    combined = trimesh.util.concatenate([cube, supports])

    return cube, supports, combined


def create_synthetic_multishell_part() -> Tuple[trimesh.Trimesh, trimesh.Trimesh, trimesh.Trimesh]:
    """Helper creating a multi-shell part (main body + disjoint floating internal island)

    Returns:
        (multishell_reference, true_supports, combined_mesh)
    """
    main_box = trimesh.creation.box(extents=(24.0, 24.0, 24.0))
    main_box.apply_translation([0.0, 0.0, 20.0])

    # Internal floating island shell
    island = trimesh.creation.box(extents=(6.0, 6.0, 6.0))
    island.apply_translation([0.0, 0.0, 20.0])

    ref_part = trimesh.util.concatenate([main_box, island])

    # 4 support pillars
    pillars = []
    for ox, oy in [(-8.0, -8.0), (8.0, -8.0), (-8.0, 8.0), (8.0, 8.0)]:
        cyl = trimesh.creation.cylinder(radius=0.5, height=10.0, sections=16)
        cyl.apply_translation([ox, oy, 8.0 - 5.0 + 0.3])
        pillars.append(cyl)

    supports = trimesh.util.concatenate(pillars)
    combined = trimesh.util.concatenate([ref_part, supports])

    return ref_part, supports, combined


class TestSupportedMeshSeparator(unittest.TestCase):
    """Test suite for SupportedMeshSeparator and split_supported_mesh."""

    def test_mode_a_reference_guided(self) -> None:
        """Test Mode A reference guided splitting with coordinate invariance and zero triangle loss."""
        ref_cube, true_supports, combined = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=12.0, penetration=0.3
        )

        part_mesh, support_mesh = split_supported_mesh(
            combined_mesh=combined,
            reference_mesh=ref_cube,
            distance_threshold=0.05,
        )

        # Assert zero triangle loss
        self.assertEqual(len(part_mesh.faces) + len(support_mesh.faces), len(combined.faces))
        self.assertEqual(len(part_mesh.faces), len(ref_cube.faces))
        self.assertEqual(len(support_mesh.faces), len(true_supports.faces))

        # Assert coordinate invariance
        self.assertTrue(np.allclose(part_mesh.bounds, ref_cube.bounds, atol=1e-5))
        self.assertTrue(np.allclose(support_mesh.bounds, true_supports.bounds, atol=1e-5))

    def test_mode_a_multishell_part(self) -> None:
        """Test Mode A correctly recovers multi-shell parts (e.g. hollowed models with islands)."""
        ref_part, true_supports, combined = create_synthetic_multishell_part()

        part_mesh, support_mesh = split_supported_mesh(
            combined_mesh=combined,
            reference_mesh=ref_part,
            distance_threshold=0.05,
        )

        # Assert zero triangle loss
        self.assertEqual(len(part_mesh.faces) + len(support_mesh.faces), len(combined.faces))
        self.assertEqual(len(part_mesh.faces), len(ref_part.faces))
        self.assertEqual(len(support_mesh.faces), len(true_supports.faces))

        # Assert coordinate invariance
        self.assertTrue(np.allclose(part_mesh.bounds, ref_part.bounds, atol=1e-5))
        self.assertTrue(np.allclose(support_mesh.bounds, true_supports.bounds, atol=1e-5))

    def test_mode_b_autonomous_heuristic_pillars(self) -> None:
        """Test Mode B autonomous heuristic splitting without reference mesh."""
        ref_cube, true_supports, combined = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=14.0, penetration=0.3
        )

        part_mesh, support_mesh = split_supported_mesh(
            combined_mesh=combined,
            reference_mesh=None,
        )

        # Assert zero triangle loss
        self.assertEqual(len(part_mesh.faces) + len(support_mesh.faces), len(combined.faces))
        self.assertEqual(len(part_mesh.faces), len(ref_cube.faces))
        self.assertEqual(len(support_mesh.faces), len(true_supports.faces))

        # Assert coordinate invariance
        self.assertTrue(np.allclose(part_mesh.bounds, ref_cube.bounds, atol=1e-5))
        self.assertTrue(np.allclose(support_mesh.bounds, true_supports.bounds, atol=1e-5))

    def test_mode_b_autonomous_with_raft(self) -> None:
        """Test Mode B identifies both support pillars and base raft."""
        ref_cube, true_supports, combined = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=14.0, penetration=0.3, with_raft=True
        )

        part_mesh, support_mesh = split_supported_mesh(
            combined_mesh=combined,
            reference_mesh=None,
        )

        # Assert zero triangle loss
        self.assertEqual(len(part_mesh.faces) + len(support_mesh.faces), len(combined.faces))
        self.assertEqual(len(part_mesh.faces), len(ref_cube.faces))
        self.assertEqual(len(support_mesh.faces), len(true_supports.faces))

        # Assert coordinate invariance
        self.assertTrue(np.allclose(part_mesh.bounds, ref_cube.bounds, atol=1e-5))
        self.assertTrue(np.allclose(support_mesh.bounds, true_supports.bounds, atol=1e-5))

    def test_extract_support_tips(self) -> None:
        """Test extract_support_tips identifies penetrating tip vertices and colors."""
        ref_cube, true_supports, _ = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=12.0, penetration=0.3
        )

        tip_res = extract_support_tips(
            part_mesh=ref_cube,
            support_mesh=true_supports,
            tip_distance_threshold=0.8,
            g_pillar=255,
            g_tip=128,
        )

        tip_indices = tip_res["tip_vertex_indices"]
        self.assertIsInstance(tip_indices, np.ndarray)
        self.assertGreater(len(tip_indices), 0)

        # Vertices of tips must be near the bottom of the cube (Z ~ 10.0)
        tip_vertices = true_supports.vertices[tip_indices]
        self.assertTrue(np.all(tip_vertices[:, 2] >= 9.0))

        # Non-tip vertices (pillar bases at Z ~ -1.7) should not be in tip_indices
        base_indices = np.where(true_supports.vertices[:, 2] < 5.0)[0]
        self.assertFalse(np.any(np.isin(base_indices, tip_indices)))

        # Check tip submesh
        tip_submesh = tip_res["tip_submesh"]
        self.assertIsInstance(tip_submesh, trimesh.Trimesh)
        self.assertGreater(len(tip_submesh.faces), 0)

        # Check vertex colors
        colored_supports = tip_res["support_mesh_with_vertex_colors"]
        self.assertIsInstance(colored_supports, trimesh.Trimesh)
        colors = colored_supports.visual.vertex_colors
        self.assertTrue(np.all(colors[tip_indices, 0] == 128))
        self.assertTrue(np.all(colors[base_indices, 0] == 255))

    def test_class_lifecycle_and_export(self) -> None:
        """Test SupportedMeshSeparator class separate, tag_tips, and export methods."""
        ref_cube, true_supports, combined = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=12.0, penetration=0.3
        )

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            comb_path = tmp_path / "combined.stl"
            ref_path = tmp_path / "ref.stl"
            combined.export(str(comb_path))
            ref_cube.export(str(ref_path))

            separator = SupportedMeshSeparator(combined_path=comb_path, reference_part_path=ref_path)
            part, supp = separator.separate()

            self.assertEqual(len(part.faces), len(ref_cube.faces))
            self.assertEqual(len(supp.faces), len(true_supports.faces))

            tagged_supp = separator.tag_tips(threshold_mm=0.8)
            self.assertIsNotNone(separator.tip_submesh)
            self.assertGreater(len(separator.tip_submesh.faces), 0)

            export_dir = tmp_path / "out"
            exported = separator.export(export_dir, prefix="job1_")

            self.assertIn("part", exported)
            self.assertIn("supports", exported)
            self.assertIn("tips", exported)

            loaded_part = trimesh.load(exported["part"], force="mesh")
            loaded_supp = trimesh.load(exported["supports"], force="mesh")
            loaded_tips = trimesh.load(exported["tips"], force="mesh")

            self.assertTrue(np.allclose(loaded_part.bounds, ref_cube.bounds, atol=1e-4))
            self.assertEqual(len(loaded_part.faces), len(ref_cube.faces))
            self.assertEqual(len(loaded_supp.faces), len(true_supports.faces))
            self.assertEqual(len(loaded_tips.faces), len(separator.tip_submesh.faces))

    def test_cli_execution(self) -> None:
        """Test CLI execution via subprocess."""
        ref_cube, _, combined = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=12.0, penetration=0.3
        )

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            comb_file = tmp_path / "plate_export.stl"
            ref_file = tmp_path / "original_model.stl"
            out_dir = tmp_path / "separated_meshes"

            combined.export(str(comb_file))
            ref_cube.export(str(ref_file))

            cmd = [
                sys.executable,
                "-m",
                "graphite.slicing.support_separator",
                "--input",
                str(comb_file),
                "--ref",
                str(ref_file),
                "--out-dir",
                str(out_dir),
                "--tip-threshold",
                "0.75",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, f"CLI stderr: {result.stderr}")

            part_out = out_dir / "part.stl"
            supports_out = out_dir / "supports.stl"
            tips_out = out_dir / "tips.stl"

            self.assertTrue(part_out.exists())
            self.assertTrue(supports_out.exists())
            self.assertTrue(tips_out.exists())

            loaded_part = trimesh.load(str(part_out), force="mesh")
            self.assertEqual(len(loaded_part.faces), len(ref_cube.faces))
            self.assertTrue(np.allclose(loaded_part.bounds, ref_cube.bounds, atol=1e-4))

    def test_cli_execution_autonomous_mode_b(self) -> None:
        """Test CLI execution in autonomous Mode B without --ref."""
        ref_cube, _, combined = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=12.0, penetration=0.3, with_raft=True
        )

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            comb_file = tmp_path / "plate_autonomous.stl"
            out_dir = tmp_path / "separated_autonomous"

            combined.export(str(comb_file))

            cmd = [
                sys.executable,
                "-m",
                "graphite.slicing.support_separator",
                "--input",
                str(comb_file),
                "--out-dir",
                str(out_dir),
                "--tip-threshold",
                "0.8",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, f"CLI stderr: {result.stderr}")

            part_out = out_dir / "part.stl"
            supports_out = out_dir / "supports.stl"
            tips_out = out_dir / "tips.stl"

            self.assertTrue(part_out.exists())
            self.assertTrue(supports_out.exists())
            self.assertTrue(tips_out.exists())

            loaded_part = trimesh.load(str(part_out), force="mesh")
            self.assertEqual(len(loaded_part.faces), len(ref_cube.faces))
            self.assertTrue(np.allclose(loaded_part.bounds, ref_cube.bounds, atol=1e-4))

    def test_detect_and_disconnect_support_tops_component_mode(self) -> None:
        """Test detecting support tops and disconnecting complete intact components."""
        # Create modular supports: 2 pillars, each with a trunk and a tip cone
        p1_trunk = trimesh.creation.cylinder(radius=1.0, height=10.0)
        p1_trunk.apply_translation([-5.0, 0.0, 5.0])
        p1_tip = trimesh.creation.cone(radius=1.0, height=2.0)
        p1_tip.apply_translation([-5.0, 0.0, 11.0])

        p2_trunk = trimesh.creation.cylinder(radius=1.0, height=10.0)
        p2_trunk.apply_translation([5.0, 0.0, 5.0])
        p2_tip = trimesh.creation.cone(radius=1.0, height=2.0)
        p2_tip.apply_translation([5.0, 0.0, 11.0])

        true_supports = trimesh.util.concatenate([p1_trunk, p1_tip, p2_trunk, p2_tip])

        bulk, tops, info = detect_and_disconnect_support_tops(
            support_mesh=true_supports,
            mode="component",
            xy_cluster_radius=2.0,
        )

        self.assertEqual(len(info), 2)
        self.assertGreater(len(tops.faces), 0)
        self.assertGreater(len(bulk.faces), 0)

        # Zero triangle loss in component mode
        self.assertEqual(len(tops.faces) + len(bulk.faces), len(true_supports.faces))
        self.assertEqual(len(tops.faces), len(p1_tip.faces) + len(p2_tip.faces))
        self.assertEqual(len(bulk.faces), len(p1_trunk.faces) + len(p2_trunk.faces))

        # Tops bounds should be located at the top contact area
        self.assertGreaterEqual(tops.bounds[1, 2], 11.5)

    def test_detect_and_disconnect_support_tops_planar_cut_mode(self) -> None:
        """Test detecting support tops and disconnecting via clean planar cut."""
        cyl = trimesh.creation.cylinder(radius=1.0, height=20.0)
        cyl.apply_translation([0, 0, 10.0])

        bulk, tops, info = detect_and_disconnect_support_tops(
            support_mesh=cyl,
            mode="planar_cut",
            top_height_mm=2.0,
        )

        self.assertEqual(len(info), 1)
        self.assertGreater(len(tops.faces), 0)
        self.assertGreater(len(bulk.faces), 0)
        self.assertAlmostEqual(tops.bounds[0, 2], 18.0, delta=0.01)
        self.assertAlmostEqual(bulk.bounds[1, 2], 18.0, delta=0.01)

    def test_cli_disconnect_tops(self) -> None:
        """Test CLI execution with --disconnect-tops flag."""
        ref_cube, _, combined = create_synthetic_supported_cube(
            cube_size=20.0, pillar_radius=0.6, pillar_height=12.0, penetration=0.3, with_raft=True
        )

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            comb_file = tmp_path / "plate_disconnect.stl"
            out_dir = tmp_path / "out_disconnect"

            combined.export(str(comb_file))

            cmd = [
                sys.executable,
                "-m",
                "graphite.slicing.support_separator",
                "--input",
                str(comb_file),
                "--out-dir",
                str(out_dir),
                "--disconnect-tops",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, f"CLI stderr: {result.stderr}")

            self.assertTrue((out_dir / "part.stl").exists())
            self.assertTrue((out_dir / "supports.stl").exists())
            self.assertTrue((out_dir / "bulk_supports.stl").exists())
            self.assertTrue((out_dir / "tops.stl").exists())

    def test_single_shell_handling(self) -> None:
        """Test edge cases with single shell or empty meshes."""
        box = trimesh.creation.box()
        part, supp = split_supported_mesh(box, reference_mesh=box)
        self.assertEqual(len(part.faces), len(box.faces))
        self.assertEqual(len(supp.faces), 0)

        # Empty mesh
        empty = trimesh.Trimesh()
        part_e, supp_e = split_supported_mesh(empty)
        self.assertEqual(len(part_e.faces), 0)
        self.assertEqual(len(supp_e.faces), 0)


if __name__ == "__main__":
    unittest.main()
