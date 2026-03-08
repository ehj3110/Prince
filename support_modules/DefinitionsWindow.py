# -*- coding: utf-8 -*-
"""
DefinitionsWindow

Tabbed reference window that explains every image-processing feature in
ImageModificationWindow.  All distances are given both in pixels and in
physical units at the assumed pixel pitch of 4 µm/px.
"""

import math
import tkinter as tk
from tkinter import Toplevel, Frame, Label, Canvas
from tkinter import ttk, font as tkFont


PITCH_UM = 4          # µm per pixel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _px(px: float) -> str:
    """Format a pixel value with its physical equivalent."""
    return f"{px:.0f} px  ({px * PITCH_UM:.0f} µm)"


def _scrollable_tab(notebook: ttk.Notebook, title: str) -> tk.Frame:
    """Return a vertically scrollable Frame attached to `notebook`."""
    outer = tk.Frame(notebook)
    notebook.add(outer, text=title)

    canvas = Canvas(outer, highlightthickness=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(win_id, width=canvas.winfo_width())

    def _on_canvas_configure(event):
        canvas.itemconfig(win_id, width=event.width)

    inner.bind("<Configure>", _on_inner_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    return inner


def _section(parent: tk.Frame, text: str, pady_top: int = 12) -> None:
    """Bold section heading with a solid horizontal rule above it."""
    # Solid separator line above heading
    sep = tk.Frame(parent, height=1, bg="#aaaaaa")
    sep.pack(fill="x", padx=12, pady=(pady_top, 0))
    f = tkFont.Font(family="Helvetica", size=11, weight="bold")
    Label(parent, text=text, font=f, anchor="w").pack(
        fill="x", padx=14, pady=(4, 2)
    )


def _para(parent: tk.Frame, text: str) -> None:
    """Body paragraph, word-wrapped."""
    body = tkFont.Font(family="Helvetica", size=10)
    Label(parent, text=text, font=body, anchor="nw", justify="left",
          wraplength=650).pack(fill="x", padx=22, pady=(0, 4))


def _param(parent: tk.Frame, name: str, desc: str) -> None:
    """Single parameter row with a dashed separator above it."""
    # Dashed gray line between parameters
    dash_canvas = Canvas(parent, height=6, highlightthickness=0, bg="white")
    dash_canvas.pack(fill="x", padx=28)
    # Draw dashed line after the widget is visible (use after to get width)
    def _draw_dash(event, c=dash_canvas):
        c.delete("dash")
        c.create_line(0, 3, c.winfo_width(), 3,
                      fill="#cccccc", dash=(4, 4), tags="dash")
    dash_canvas.bind("<Configure>", _draw_dash)

    row = tk.Frame(parent)
    row.pack(fill="x", padx=28, pady=(0, 4))
    bold = tkFont.Font(family="Helvetica", size=10, weight="bold")
    body = tkFont.Font(family="Helvetica", size=10)
    Label(row, text=f"{name}: ", font=bold, anchor="nw").pack(side="left")
    Label(row, text=desc, font=body, anchor="nw", justify="left",
          wraplength=560).pack(side="left", fill="x", expand=True)


def _divider(parent: tk.Frame) -> None:
    sep = tk.Frame(parent, height=1, bg="#aaaaaa")
    sep.pack(fill="x", padx=12, pady=6)


# ---------------------------------------------------------------------------
# Canvas diagrams
# ---------------------------------------------------------------------------

def _draw_gaussian_curves(parent: tk.Frame) -> Canvas:
    """
    Draw two Gaussian bell curves on one canvas:
    narrow (small σ) and wide (large σ), with σ markers.
    """
    W, H = 580, 180
    c = Canvas(parent, width=W, height=H, bg="#f8f8f8",
               relief="groove", borderwidth=1)
    c.pack(padx=22, pady=(4, 10))

    PAD_L, PAD_R, PAD_T, PAD_B = 40, 20, 16, 36
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    def gx(x_norm):   # x_norm in [-1, 1] → canvas x
        return PAD_L + (x_norm + 1) / 2 * plot_w

    def gy(y_norm):   # y_norm in [0, 1] → canvas y (inverted)
        return PAD_T + (1 - y_norm) * plot_h

    # Axes
    c.create_line(PAD_L, PAD_T, PAD_L, PAD_T + plot_h, fill="#888", width=1)
    c.create_line(PAD_L, PAD_T + plot_h, W - PAD_R, PAD_T + plot_h, fill="#888", width=1)

    def gauss(x_norm, sig_norm):
        return math.exp(-(x_norm ** 2) / (2 * sig_norm ** 2))

    def draw_curve(sig_norm, color, label, label_x_norm):
        pts = []
        N = 200
        for i in range(N + 1):
            xn = -1 + 2 * i / N
            yn = gauss(xn, sig_norm)
            pts += [gx(xn), gy(yn)]
        c.create_line(pts, fill=color, width=2, smooth=True)
        # label
        lx = gx(label_x_norm)
        ly = gy(gauss(label_x_norm, sig_norm)) - 6
        c.create_text(lx, ly, text=label, fill=color, font=("Helvetica", 9, "bold"),
                      anchor="s")

    draw_curve(0.18, "#1a6fbf", "small σ  (narrow)", -0.28)
    draw_curve(0.35, "#bf4a1a", "large σ  (wide)", -0.55)

    # σ marker on narrow curve
    sig_n = 0.18
    x_sig = sig_n
    y_sig = gauss(x_sig, sig_n)
    c.create_line(gx(0), gy(0), gx(0), PAD_T + plot_h, fill="#1a6fbf", dash=(3, 3), width=1)
    c.create_line(gx(x_sig), gy(y_sig), gx(x_sig), PAD_T + plot_h,
                  fill="#1a6fbf", dash=(3, 3), width=1)
    c.create_text(gx(x_sig / 2), PAD_T + plot_h + 12, text="σ",
                  fill="#1a6fbf", font=("Helvetica", 9, "italic"))

    # x-axis label
    c.create_text(W // 2, H - 4, text="Position →", fill="#555",
                  font=("Helvetica", 8))
    # y-axis label
    c.create_text(10, PAD_T + plot_h // 2, text="Amplitude", fill="#555",
                  font=("Helvetica", 8), angle=90)
    return c


def _draw_edge_enhancement_profile(parent: tk.Frame) -> Canvas:
    """
    1D cross-section at a part edge:
    original (step), blurred (S-curve), enhanced = original − blurred (peak).
    """
    W, H = 580, 190
    c = Canvas(parent, width=W, height=H, bg="#f8f8f8",
               relief="groove", borderwidth=1)
    c.pack(padx=22, pady=(4, 8))

    PAD_L, PAD_R, PAD_T, PAD_B = 44, 20, 16, 38
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    N = 300
    xs = [-1 + 2 * i / N for i in range(N + 1)]

    def sigmoid(x, k=8):
        return 1 / (1 + math.exp(-k * x))

    # Original: step at x=0
    orig = [sigmoid(x, k=30) for x in xs]
    # Blurred: smooth sigmoid
    sig_val = 0.22
    blurred = [sigmoid(x, k=1 / sig_val) for x in xs]
    # Enhanced = orig − blurred, normalised to [0, 1]
    diff_raw = [o - b for o, b in zip(orig, blurred)]
    d_min, d_max = min(diff_raw), max(diff_raw)
    d_range = d_max - d_min if d_max > d_min else 1.0
    enhanced = [(d - d_min) / d_range for d in diff_raw]

    def gx(i):
        return PAD_L + (xs[i] + 1) / 2 * plot_w

    def gy(v):
        return PAD_T + (1 - v) * plot_h

    # Axes
    c.create_line(PAD_L, PAD_T, PAD_L, PAD_T + plot_h, fill="#888", width=1)
    c.create_line(PAD_L, PAD_T + plot_h, W - PAD_R, PAD_T + plot_h, fill="#888", width=1)

    # Edge marker
    edge_x = PAD_L + plot_w // 2
    c.create_line(edge_x, PAD_T, edge_x, PAD_T + plot_h,
                  fill="#ccc", dash=(4, 3), width=1)
    c.create_text(edge_x + 3, PAD_T + 5, text="edge", fill="#999",
                  font=("Helvetica", 8), anchor="nw")

    # Background shading: left = black resin, right = white part
    c.create_rectangle(PAD_L, PAD_T, edge_x, PAD_T + plot_h,
                       fill="#e8e8e8", outline="")
    c.create_rectangle(edge_x, PAD_T, W - PAD_R, PAD_T + plot_h,
                       fill="#fff8f0", outline="")
    c.create_text(PAD_L + (edge_x - PAD_L) // 2, PAD_T + plot_h - 6,
                  text="black", fill="#aaa", font=("Helvetica", 8))
    c.create_text(edge_x + (W - PAD_R - edge_x) // 2, PAD_T + plot_h - 6,
                  text="white (part)", fill="#cca070", font=("Helvetica", 8))

    def draw_line(vals, color, label, label_xi):
        pts = []
        for i, v in enumerate(vals):
            pts += [gx(i), gy(v)]
        c.create_line(pts, fill=color, width=2, smooth=True)
        lx = gx(label_xi)
        ly = gy(vals[label_xi]) - 8
        c.create_text(lx, ly, text=label, fill=color,
                      font=("Helvetica", 8, "bold"), anchor="s")

    draw_line(orig,     "#aaaaaa", "Original",   int(0.85 * N))
    draw_line(blurred,  "#888800", "Blurred",     int(0.75 * N))
    draw_line(enhanced, "#1a6fbf", "Enhanced",    int(0.60 * N))

    # Axis labels
    c.create_text(W // 2, H - 4, text="Position across edge →",
                  fill="#555", font=("Helvetica", 8))
    c.create_text(10, PAD_T + plot_h // 2, text="Intensity", fill="#555",
                  font=("Helvetica", 8), angle=90)
    return c


def _draw_global_profile(parent: tk.Frame) -> Canvas:
    """
    Radial 1D multiplier map: center = globe value, edge = 1.0.
    Shows small σ (steep) vs large σ (gentle) versions.
    """
    W, H = 580, 170
    c = Canvas(parent, width=W, height=H, bg="#f8f8f8",
               relief="groove", borderwidth=1)
    c.pack(padx=22, pady=(4, 8))

    PAD_L, PAD_R, PAD_T, PAD_B = 44, 20, 16, 38
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    globe = 0.8   # example

    def gx(r_norm):  # r_norm in [0, 1]
        return PAD_L + r_norm * plot_w

    def gy(v):  # v in [0, 1]
        return PAD_T + (1 - v) * plot_h

    # Axes
    c.create_line(PAD_L, PAD_T, PAD_L, PAD_T + plot_h, fill="#888", width=1)
    c.create_line(PAD_L, PAD_T + plot_h, W - PAD_R, PAD_T + plot_h, fill="#888", width=1)

    # y tick: globe value
    gy_globe = gy(globe)
    c.create_line(PAD_L - 4, gy_globe, PAD_L, gy_globe, fill="#888", width=1)
    c.create_text(PAD_L - 6, gy_globe, text=f"{globe}", fill="#555",
                  font=("Helvetica", 8), anchor="e")
    gy_one = gy(1.0)
    c.create_line(PAD_L - 4, gy_one, PAD_L, gy_one, fill="#888", width=1)
    c.create_text(PAD_L - 6, gy_one, text="1.0", fill="#555",
                  font=("Helvetica", 8), anchor="e")

    N = 200

    def ge_val(r_norm, sig_div):
        # sigma = 1.0 / sig_div in normalised units
        sig = 1.0 / sig_div
        g = math.exp(-(r_norm ** 2) / (2 * sig ** 2))
        inverted = 1.0 - g
        return globe + (1.0 - globe) * inverted

    for sig_div, color, label in [(4, "#1a6fbf", "low σ (steep)"),
                                   (2, "#bf4a1a", "high σ (gentle)")]:
        pts = []
        for i in range(N + 1):
            r = i / N
            v = ge_val(r, sig_div)
            pts += [gx(r), gy(v)]
        c.create_line(pts, fill=color, width=2, smooth=True)
        mid_i = N // 2
        r_m = mid_i / N
        lx = gx(r_m)
        ly = gy(ge_val(r_m, sig_div)) - 8
        c.create_text(lx, ly, text=label, fill=color,
                      font=("Helvetica", 8, "bold"), anchor="s")

    c.create_text(W // 2, H - 4,
                  text="Radial distance from image centre →  (0 = centre, 1 = edge)",
                  fill="#555", font=("Helvetica", 8))
    c.create_text(10, PAD_T + plot_h // 2, text="Multiplier", fill="#555",
                  font=("Helvetica", 8), angle=90)
    return c


def _draw_scatter_profile(parent: tk.Frame) -> Canvas:
    """
    1D cross-section: Gaussian-based boundary dimming.
    Shows original flat intensity vs scatter-compensated output.
    """
    W, H = 580, 180
    c = Canvas(parent, width=W, height=H, bg="#f8f8f8",
               relief="groove", borderwidth=1)
    c.pack(padx=22, pady=(4, 8))

    PAD_L, PAD_R, PAD_T, PAD_B = 44, 20, 16, 38
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    N = 300
    xs = [i / N for i in range(N + 1)]   # 0 = left edge, 1 = right edge

    # Part occupies middle 60%
    left_edge  = 0.20
    right_edge = 0.80

    def inside(x):
        return left_edge <= x <= right_edge

    # Original: flat 1.0 inside part, 0 outside
    orig = [1.0 if inside(x) else 0.0 for x in xs]

    # Compensated: Gaussian dip at each boundary (inverted edge enhancement)
    sig = 0.07   # in normalised units (≈ 21 px at N=300)

    def gauss_dip(x):
        if not inside(x):
            return 0.0
        dl = x - left_edge
        dr = right_edge - x
        dist = min(dl, dr)
        # Gaussian weight centred at boundary (dist=0)
        g = math.exp(-(0 ** 2) / (2 * sig ** 2)) - math.exp(-(dist ** 2) / (2 * sig ** 2))
        strength = 0.5
        multiplier = 1.0 - strength * (1 - min(dist / (3 * sig), 1.0)) ** 2
        return multiplier

    compensated = [gauss_dip(x) for x in xs]

    def gx(i):
        return PAD_L + xs[i] * plot_w

    def gy(v):
        return PAD_T + (1 - v) * plot_h

    # Background shading
    le_px = PAD_L + int(left_edge * plot_w)
    re_px = PAD_L + int(right_edge * plot_w)
    c.create_rectangle(PAD_L, PAD_T, le_px, PAD_T + plot_h,
                       fill="#e8e8e8", outline="")
    c.create_rectangle(le_px, PAD_T, re_px, PAD_T + plot_h,
                       fill="#fff8f0", outline="")
    c.create_rectangle(re_px, PAD_T, W - PAD_R, PAD_T + plot_h,
                       fill="#e8e8e8", outline="")
    for xp, lbl in [(PAD_L + (le_px - PAD_L) // 2, "resin"),
                    (le_px + (re_px - le_px) // 2,  "part"),
                    (re_px + (W - PAD_R - re_px) // 2, "resin")]:
        c.create_text(xp, PAD_T + plot_h - 6, text=lbl, fill="#aaa",
                      font=("Helvetica", 8))

    # Edge markers
    for ex in (le_px, re_px):
        c.create_line(ex, PAD_T, ex, PAD_T + plot_h,
                      fill="#ccc", dash=(4, 3), width=1)

    # Axes
    c.create_line(PAD_L, PAD_T, PAD_L, PAD_T + plot_h, fill="#888", width=1)
    c.create_line(PAD_L, PAD_T + plot_h, W - PAD_R, PAD_T + plot_h, fill="#888", width=1)

    def draw_line(vals, color, label, label_xi):
        pts = []
        for i, v in enumerate(vals):
            pts += [gx(i), gy(v)]
        c.create_line(pts, fill=color, width=2, smooth=False)
        lx = gx(label_xi)
        ly = gy(vals[label_xi]) - 10
        c.create_text(lx, ly, text=label, fill=color,
                      font=("Helvetica", 8, "bold"), anchor="s")

    mid = (N * 2) // 5
    draw_line(orig,        "#aaaaaa", "Original",    mid + 30)
    draw_line(compensated, "#1a6fbf", "Compensated", mid - 20)

    c.create_text(W // 2, H - 4,
                  text="Position across part →",
                  fill="#555", font=("Helvetica", 8))
    c.create_text(10, PAD_T + plot_h // 2, text="Intensity", fill="#555",
                  font=("Helvetica", 8), angle=90)
    return c


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

def _build_sigma_tab(nb: ttk.Notebook) -> None:
    f = _scrollable_tab(nb, "Gaussian σ")

    _section(f, "What is a Gaussian?", pady_top=10)
    _para(f, (
        "A Gaussian (bell curve) is a smooth, symmetric function centred at zero.  "
        "In image processing it describes how an operation's influence falls off with "
        "distance — strong at the centre, tapering exponentially to zero at the tails.  "
        "It is the natural model for optical blur, LED scatter, and many other "
        "physical spreading phenomena."
    ))

    _draw_gaussian_curves(f)

    _section(f, "What does σ control?")
    _para(f, (
        "σ (sigma) is the standard deviation of the Gaussian.  It sets the WIDTH of "
        "the bell:\n"
        "  •  68 % of the area falls within ±1σ of centre.\n"
        "  •  95 % falls within ±2σ.\n"
        "  •  99.7 % falls within ±3σ.\n\n"
        "A small σ produces a narrow, sharp effect.  A large σ produces a broad, "
        "gradual effect.  In all features below, σ is given in pixels; multiply by "
        f"{PITCH_UM} µm to get the physical distance."
    ))

    _section(f, "Quick reference — σ → physical distance")
    rows = [
        (" σ = 5 px",  f"{5*PITCH_UM} µm",  "thin fibre / very narrow band"),
        (" σ = 15 px", f"{15*PITCH_UM} µm", "narrow edge / fine feature"),
        (" σ = 25 px", f"{25*PITCH_UM} µm", "typical edge enhancement width"),
        (" σ = 50 px", f"{50*PITCH_UM} µm", "half-width of a ~400 µm strut"),
        (" σ = 100 px",f"{100*PITCH_UM} µm","global-scale gradient"),
    ]
    tbl = tk.Frame(f, relief="groove", borderwidth=1)
    tbl.pack(padx=28, pady=(2, 10), anchor="w")
    hdr = tkFont.Font(family="Helvetica", size=9, weight="bold")
    bdy = tkFont.Font(family="Helvetica", size=9)
    for h, rt in [("σ (pixels)", "Physical (µm)"), ("Pixels", "Micrometres")]:
        pass
    for hdr_txt, val_txt, note in [("σ (px)", "Distance", "Note")] + rows:
        row_f = tk.Frame(tbl)
        row_f.pack(fill="x")
        for txt, w, anchor in [(hdr_txt, 10, "e"), (val_txt, 12, "e"), (note, 36, "w")]:
            fnt = hdr if hdr_txt == "σ (px)" else bdy
            Label(row_f, text=txt, font=fnt, width=w, anchor=anchor,
                  relief="ridge", borderwidth=0, padx=4).pack(side="left")


def _build_ee_tab(nb: ttk.Notebook) -> None:
    f = _scrollable_tab(nb, "Edge Enhancement")

    _section(f, "Purpose", pady_top=10)
    _para(f, (
        "The projection will naturally have a slight Gaussian blur that softens part "
        "boundaries and makes the effective intensity lower.  Edge Enhancement "
        "counteracts this by boosting intensity at the part boundary so that the "
        "final print is closer to the intended shape."
    ))

    _section(f, "How it works")
    _para(f, (
        "A Gaussian-blurred copy of the slice image is subtracted from the original.  "
        "The result isolates the high-frequency edge signal.  That signal is then "
        "rescaled to the [Min, Max] intensity range.  Black pixels are untouched."
    ))
    _para(f, "Signal = Original − GaussianBlur(Original, σ = Blur)")

    _draw_edge_enhancement_profile(f)

    _section(f, "Parameters")
    _param(f, "Enable",
           "Toggles the feature on/off.  Leave off if your optical system is well "
           "characterised or if edge ringing is visible.")
    _param(f, "Blur  (σ)",
           f"Gaussian sigma controlling the width of the enhanced edge band.  "
           f"This is effectively how much of the edge should be 'sharp'.  "
           f"Smaller parts will require a smaller sigma value so that the edges are "
           f"still more pronounced.  A larger part will need a higher sigma value, as well.\n"
           f"  •  σ = 10 px  →  {_px(10)} band  (sharp optics)\n"
           f"  •  σ = 25 px  →  {_px(25)} band  (default)\n"
           f"  •  σ = 50 px  →  {_px(50)} band  (heavy optical blur)\n"
           f"Larger values produce a wider, more pronounced edge ring.  "
           f"Too large → visible bright halo and the edges cure when the bulk part does not; "
           f"too small → under-correction and it has no effect.")
    _param(f, "Falloff  (101)",
           f"Explicit kernel size (in pixels) used when building the Gaussian blur that "
           f"extracts the edge signal.  Must be an odd integer; even values are rounded up.\n"
           f"  •  0 (or blank) → auto: 4\u00d7Blur+1 (default behaviour)\n"
           f"  •  Set explicitly to a smaller odd number to prevent the gaussian window \n"
           f"    from spanning across narrow features (e.g. lattice struts).\n"
           f"Default 101 = 4\u00d725+1 matches the default Blur of 25.\n"
           f"Reducing Falloff while keeping Blur large produces a wide-sigma Gaussian \n"
           f"that is truncated early, giving a softer, shorter-range edge band.")
    _param(f, "Min  (100)",
           "Minimum output intensity for non-zero pixels after normalisation.  "
           "Keeps dark areas above the resin cure threshold.  "
           "Increase to 120–140 if thin features are disappearing.")
    _param(f, "Max  (255)",
           "Maximum output intensity.  Normally 255 (full exposure).  "
           "Will almost never change this.")

    _section(f, "Interaction with other features")
    _para(f, (
        "Edge Enhancement runs FIRST in the pipeline.  Its output feeds directly "
        "into Global Enhancement and Scattering Compensation."
    ))


def _build_ge_tab(nb: ttk.Notebook) -> None:
    f = _scrollable_tab(nb, "Global Enhancement")

    _section(f, "Purpose", pady_top=10)
    _para(f, (
        "For continuous printing, the resin that flows to the center of the part will "
        "partially cure as it passes under other sections of already curing part.  "
        "Global Enhancement applies a Gaussian mask that compensates for this by "
        "lowering the grayscale of the image the closer it is to the center.  "
        "That way, it tries to ensure dosage delivery is equivalent across the field."
    ))

    _section(f, "How it works")
    _para(f, (
        "A 2D vignette (correction) map is built: it equals Globe ratio at the image "
        "centre and ramps up to 1.0 at the part boundary.  Every pixel is multiplied "
        "by its map value.  Centre pixels are dimmed; edge pixels are left unchanged.  "
        "Asymmetric mode adapts the map per quadrant to handle non-circular "
        "non-uniformity."
    ))

    _draw_global_profile(f)

    _section(f, "Parameters")
    _param(f, "Enable",
           "Toggles the feature on/off.")
    _param(f, "Globe ratio  (0.8)",
           "Multiplier applied at the very centre of the image (relative to 1.0 at "
           "the part edge).  0.8 means the centre pixels receive 80 % of the edge "
           "exposure.  Lower values = stronger centre dimming.\n"
           "  •  0.7 → mild correction (Higher UV-absorber content or not very dense features)\n"
           "  •  0.25 → strong correction (Scattering resin, low UV-Abs concentration, very dense features)")
    _param(f, "Sigma  (6.0)",
           "Controls how gradually the map transitions from the centre value to 1.0.  "
           "This is NOT a pixel sigma — it is a divisor applied to the image diagonal.  "
           "Larger Sigma value → faster transition (steeper gradient, correction "
           "concentrated near the centre).  "
           "Smaller Sigma value → gentler, broader gradient.\n"
           "  •  Sigma = 4 → steep, correction only within the inner ~25 % of the field\n"
           "  •  Sigma = 8 → gentle, correction spread across the whole field")
    _param(f, "Asymmetric",
           "Splits the image into four quadrants (N/E/S/W).  Each quadrant's "
           "furthest white pixel defines its own radial extent, allowing the map to "
           "compensate for directionally non-symmetric UV distributions (e.g., from a "
           "rectangular or off-axis lamp).")
    _param(f, "Blend  (°)",
           "Angular blending width between quadrant boundaries in asymmetric mode.  "
           "A larger angle (e.g., 30°) gives smoother quadrant transitions at the "
           "cost of reducing the per-quadrant independence.  20° is a good default.")

    _section(f, "Calibration tip")
    _para(f, (
        "Print a dense gyroid scaffold with a diameter about the size of the print "
        "window.  Ensure the print parameters are set such that the edges of the "
        "scaffold are the approximate cure width and height that you want.  "
        "Measure the ratio of the scaffold's diameter to the diameter of the "
        "overcured section in the center of the scaffold.  This informs the Globe "
        "value to use."
    ))


def _build_pad_tab(nb: ttk.Notebook) -> None:
    f = _scrollable_tab(nb, "Image Padding")

    _section(f, "Purpose", pady_top=10)
    _para(f, (
        "Adds a black frame between each layer to ensure resin can reflow adequately."
    ))

    _section(f, "How it works")
    _para(f, (
        "For each source image (e.g., '5.png') a companion fully black image "
        "('5_1.png') is written alongside it in the output folder.  The output folder "
        "will therefore contain twice as many files as the input."
    ))


def _build_fd_tab(nb: ttk.Notebook) -> None:
    f = _scrollable_tab(nb, "Feature Depth Correction")

    _section(f, "Purpose", pady_top=10)
    _para(f, (
        "In lattice or micro-channel geometries, fresh resin must flow through narrow "
        "black channels to reach the white pixels before each exposure.  As it travels, "
        "scattered UV from adjacent white pixels partially pre-cures the resin.  "
        "Pixels deep inside the lattice receive 'stale' (partially cured) resin, "
        "leading to overcuring and closed channels.  Feature Depth Correction dims "
        "those interior pixels proportionally to how stale their resin supply is."
    ))

    _para(f, (
        "⚠  This is an experimental feature—it is present on this machine but NOT "
        "included in the export package.  Results are geometry-dependent; always "
        "validate on a test print before production use."
    ))

    _section(f, "Distance mode  (fast)")
    _para(f, (
        "Estimates resin staleness from pure geometry:\n"
        "  1. Classify black pixels as open channels (connected to the outer resin "
        "bath) or enclosed pores (sealed inside the part).\n"
        "  2. Find the 'outer resin pool' — the first ring of open-channel pixels "
        "immediately outside the part perimeter.  These have depth = 0.\n"
        "  3. Compute Euclidean distance from every open-channel pixel to the nearest "
        "outer-pool pixel.  Deeper channels accumulate more depth.\n"
        "  4. Spread channel depth into the adjacent white pixels via Gaussian blur.\n"
        "  5. Effective depth = (distance to nearest channel) + (channel depth).\n"
        "  6. Normalise and apply the dimming multiplier."
    ))

    _section(f, "Pressure / PDE mode  (physics model)")
    _para(f, (
        "Solves the 2D Poisson equation  ∇·(K ∇P) = −Q  for resin pressure:\n"
        "  •  K = Conductivity in open channels  (fast resin flow)\n"
        "  •  K = 1 in solid pixels              (slow seepage)\n"
        "  •  Q = Sink strength at white pixels  (resin consumption)\n"
        "  •  P = 0 at the outer pool            (Dirichlet boundary condition)\n\n"
        "High P = high vacuum = more effort to pull fresh resin to that point = more "
        "pre-curing.  Unlike distance mode, this captures channel WIDTH effects: a "
        "narrow channel resists flow more than a wide one."
    ))

    _section(f, "Parameters")
    _param(f, "Enable",
           "Toggles Feature Depth Correction on/off.")
    _param(f, "Strength  (0.4)",
           "Fractional dimming applied at the deepest pixel.  A pixel at normalised "
           "depth 1.0 is multiplied by (1 − Strength).  Strength = 0.4 → deepest "
           "pixel retains 60 % intensity.  Start low (0.2–0.4) and increase until "
           "channels are open in the print.")
    _param(f, "Smooth  (px)",
           f"Gaussian sigma for smoothing the final depth map.  Removes sharp "
           f"ridges along the medial axis of struts.  Default 10 px = {_px(10)}.")
    _param(f, "Mode",
           "Distance = fast, geometry-based.  Pressure/PDE = physics model; slower "
           "but captures channel width and local resin density effects.")
    _param(f, "Channel decay  (px) — distance mode",
           f"Controls how far the 'fresh resin influence' spreads from the outer pool "
           f"into the channels before it is considered stale.  Default 50 px = {_px(50)}.  "
           f"Increase for coarser lattices; decrease for very fine channels.")
    _param(f, "Conductivity — pressure mode",
           "Ratio of channel conductivity to solid conductivity.  Higher values "
           "(100–500) make the gradient steeper: the interior starvation is more "
           "pronounced relative to the outer edge.")
    _param(f, "Sink — pressure mode",
           "Resin consumption rate at white pixels per iteration.  Higher values "
           "increase the overall pressure magnitude.  0.05–0.2 is a useful range.")




def _build_scatter_tab(nb: ttk.Notebook) -> None:
    f = _scrollable_tab(nb, "Scattering Compensation")

    _section(f, "Purpose", pady_top=10)
    _para(f, (
        "Highly scattering resins (e.g., filled composites, pigmented materials) "
        "laterally scatter UV photons beyond the intended part boundary.  This causes "
        "overcuring horizontally, and for dense lattices to become solid.  "
        "Scattering Compensation pre-dims pixels near the part boundary so that after "
        "lateral scatter the net deposited dose is confined to the intended region."
    ))

    _section(f, "How it works")
    _para(f, (
        "This is the mathematical INVERSE of Edge Enhancement:\n\n"
        "  Edge Enhancement:  Output = Original − Blur(Original)\n"
        "  Scattering Comp:   Output = Blur(Original) − Original\n\n"
        "The result is a Gaussian-shaped DIP at each boundary: the edge pixels are "
        "dimmed, the interior pixels are bright, and the transition follows the same "
        "Gaussian profile that describes the physical scatter.  The output is "
        "rescaled so that interior pixels reach Max and boundary pixels fall to "
        "(1 − Strength) × Max."
    ))

    _draw_scatter_profile(f)

    _section(f, "Parameters")
    _param(f, "Enable",
           "Toggles Scattering Compensation on/off.")
    _param(f, "Blur",
           f"Gaussian sigma controlling how far inward from the boundary the dimming "
           f"extends.  Set this to the estimated lateral scatter radius of your resin.\n"
           f"  •  Blur = 5   →  {_px(5)}   (low-scatter resin, fine features)\n"
           f"  •  Blur = 15  →  {_px(15)}  (default)\n"
           f"  •  Blur = 25  →  {_px(25)}  (high-scatter filled resin)\n"
           f"  •  Blur = 40  →  {_px(40)}  (strongly scattering composite)\n"
           f"The Gaussian profile means the dimming tapers naturally: most "
           f"correction at the exact boundary, fading to zero approximately 3× Blur "
           f"({3*15*PITCH_UM} \u00b5m at default) inward.")
    _param(f, "Falloff  (61)",
           f"Explicit kernel size (in pixels) used when building the Gaussian blur that "
           f"extracts the scatter signal.  Must be an odd integer; even values are rounded up.\n"
           f"  •  0 (or blank) → auto: 4\u00d7Blur+1 (default behaviour)\n"
           f"  •  Reduce for dense lattices to prevent the blur kernel from spanning \n"
           f"    multiple struts simultaneously (cross-strut interference).\n"
           f"Default 61 = 4\u00d715+1 matches the default Blur of 15.\n"
           f"Example: Blur=30, Falloff=31 limits the kernel to ~one strut width \n"
           f"while still applying a broad sigma gradient.")
    _param(f, "Min  (127)",
           "Output intensity at the exact part boundary (the darkest output value).  "
           "Directly analogous to the Min parameter in Edge Enhancement.\n"
           "  •  Min = 200 → boundary pixels dim to ~78 % (mild)\n"
           "  •  Min = 127 → boundary pixels dim to ~50 % (default)\n"
           "  •  Min =  51 → boundary pixels dim to ~20 % (aggressive)\n"
           "  •  Min =   0 → boundary pixels go fully black\n"
           "Note: if Min is too low, thin features may disappear.  "
           "Decrease cautiously while monitoring minimum feature width in preview.")
    _param(f, "Max  (255)",
           "Output intensity at the interior of the part (the brightest output value).  "
           "Normally 255.  Matches the Max parameter in Edge Enhancement.  "
           "Will almost never change this.")

    _section(f, "Relationship to Edge Enhancement")
    _para(f, (
        "Edge Enhancement and Scattering Compensation are conceptually opposite.  "
        "Using both simultaneously is possible but produces competing effects at the "
        "boundary \u2014 the net result depends on the relative Min and Sigma values.  "
        "In practice, choose one based on whether your optical system blurs "
        "(\u2192 EE) or your resin scatters (\u2192 SC)."
    ))

    _section(f, "Tuning workflow")
    _para(f, (
        "1. Print a calibration target with known 200 \u00b5m lines and spaces.\n"
        "2. Measure the printed line width under a microscope.\n"
        "3. If printed width > CAD width, decrease Min incrementally.\n"
        "4. Adjust Blur to match the scatter radius:  "
        "Blur ≈ (printed_excess_width / 2) / pixel_pitch.\n"
        "   Example: 60 µm excess on each side → Blur ≈ 60 / 4 = 15."
    ))


def _build_pipeline_tab(nb: ttk.Notebook) -> None:
    f = _scrollable_tab(nb, "Pipeline Order")

    _section(f, "Processing order", pady_top=10)
    _para(f, (
        "All enabled features are applied in a fixed sequence per slice image:\n"
    ))

    steps = [
        ("1", "Edge Enhancement",        "Sharpens boundaries by subtracting a blurred copy."),
        ("2", "Global Enhancement",       "Applies radial multiplier map for lamp non-uniformity."),
        ("3", "Feature Depth Correction", "Dims interior pixels proportional to resin staleness."),
        ("4", "Scattering Compensation",  "Dims boundary pixels proportional to scatter radius."),
        ("5", "Image Padding",             "Inserts a black gap frame between each layer."),
    ]

    tbl = tk.Frame(f, relief="groove", borderwidth=1)
    tbl.pack(padx=28, pady=(4, 12), anchor="w")
    hdr = tkFont.Font(family="Helvetica", size=9, weight="bold")
    bdy = tkFont.Font(family="Helvetica", size=9)
    for step_n, name, desc in [("Step", "Feature", "Action")] + steps:
        row_f = tk.Frame(tbl, bg="#f0f0f0" if step_n == "Step" else "white")
        row_f.pack(fill="x")
        fnt = hdr if step_n == "Step" else bdy
        for txt, w, anchor in [(step_n, 5, "c"), (name, 26, "w"), (desc, 55, "w")]:
            Label(row_f, text=txt, font=fnt, width=w, anchor=anchor,
                  padx=4, pady=2, relief="ridge",
                  bg="#f0f0f0" if step_n == "Step" else "white").pack(side="left")

    _section(f, "Why order matters")
    _para(f, (
        "Edge Enhancement produces a re-normalised image — running Global Enhancement "
        "after it ensures the vignette map is applied to the sharpened signal, not the "
        "raw one.  Feature Depth Correction uses the current pixel intensities to "
        "build its depth map, so it benefits from having the boundary already "
        "sharpened.  Scattering Compensation runs last so it dims the already-"
        "processed boundary without being undone by subsequent normalisation steps.  "
        "Image Padding always runs independently and inserts black frames regardless "
        "of which other features are active."
    ))


# ---------------------------------------------------------------------------
# Main window class
# ---------------------------------------------------------------------------

class DefinitionsWindow:
    def __init__(self, master_window):
        self.window = Toplevel(master_window)
        self.window.title("Image Modification — Feature Definitions")
        self.window.geometry("740x640")
        self.window.resizable(True, True)

        title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        Label(self.window,
              text="Feature Definitions  ·  pixel pitch = 4 µm",
              font=title_font).pack(side="top", pady=(8, 4))
        Label(self.window,
              text="All σ / width values in pixels; physical distances shown in µm assuming 4 µm/px.",
              font=tkFont.Font(family="Helvetica", size=9),
              fg="#666").pack(side="top", pady=(0, 6))

        nb = ttk.Notebook(self.window)
        nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        _build_sigma_tab(nb)
        _build_ee_tab(nb)
        _build_ge_tab(nb)
        _build_pad_tab(nb)
        _build_fd_tab(nb)
        _build_scatter_tab(nb)
        _build_pipeline_tab(nb)


# ---------------------------------------------------------------------------
# Standalone launch
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = DefinitionsWindow(root)
    app.window.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
