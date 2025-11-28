"""
Create a flowchart visualization of the Adaptive Sandwich Routine
with proper spacing accounting for box heights and widths
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Create figure with better spacing
fig, ax = plt.subplots(1, 1, figsize=(16, 28))
ax.set_xlim(0, 12)
ax.set_ylim(0, 40)
ax.axis('off')

# Define colors
color_start = '#4CAF50'
color_process = '#2196F3'
color_decision = '#FF9800'
color_adaptive = '#F44336'
color_complete = '#9C27B0'

def draw_box(ax, x, y, w, h, text, color, fontsize=10):
    """Draw a rectangular box with text - (x,y) is CENTER of box"""
    box = FancyBboxPatch((x-w/2, y-h/2), w, h, 
                          boxstyle="round,pad=0.15", 
                          edgecolor='black', facecolor=color, 
                          linewidth=2.5)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', 
            fontsize=fontsize, weight='bold', wrap=True)

def draw_diamond(ax, x, y, w, h, text, color, fontsize=9):
    """Draw a diamond (decision) shape - (x,y) is CENTER"""
    diamond = mpatches.FancyBboxPatch((x-w/2, y-h/2), w, h,
                                       boxstyle="round,pad=0.1",
                                       edgecolor='black', facecolor=color,
                                       linewidth=2.5, transform=ax.transData)
    # Rotate to make diamond
    t = mpatches.transforms.Affine2D().rotate_deg_around(x, y, 45) + ax.transData
    diamond.set_transform(t)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center', 
            fontsize=fontsize, weight='bold')

def draw_arrow(ax, x1, y1, x2, y2, label=''):
    """Draw an arrow"""
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                           arrowstyle='->', mutation_scale=25,
                           linewidth=2.5, color='black')
    ax.add_patch(arrow)
    if label:
        mid_x, mid_y = (x1+x2)/2, (y1+y2)/2
        ax.text(mid_x+0.4, mid_y, label, fontsize=9, 
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='gray', linewidth=1))

# Y positions - PROPERLY ACCOUNTING FOR BOX HEIGHTS
y_pos = 38
gap = 0.8  # Vertical gap between elements
x_main = 6  # X position for main flow
x_adapt = 10  # X position for adaptive branch

# START (h=0.8)
h_box = 0.8
draw_box(ax, x_main, y_pos, 3, h_box, 'START SANDWICH\n(After Return Movement)', color_start)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap)
y_pos = y_bottom - gap

# Initialize speeds (h=1.0)
h_box = 1.0
y_pos -= h_box/2  # Move to center of next box
draw_box(ax, x_main, y_pos, 3.5, h_box, 'Initialize 3-Tier Speeds\nTier1 = Base\nTier2 = Base ÷ 3\nTier3 = Base ÷ 9', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap)
y_pos = y_bottom - gap

# Check adaptive override (diamond, h~1.5 effective)
h_diamond = 1.5
y_pos -= h_diamond/2
draw_diamond(ax, x_main, y_pos, 1.5, 1.5, 'Adaptive\nSpeed\nSet?', color_decision)
draw_arrow(ax, x_main + 0.8, y_pos, x_adapt, y_pos, 'YES')
draw_box(ax, x_adapt, y_pos, 1.8, 0.7, 'Use Adaptive\nSpeed', color_adaptive)
y_bottom = y_pos - h_diamond/2 - 0.3  # Extra clearance for diamond
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap, 'NO')
y_pos = y_bottom - gap

# Descent loop (h=0.9)
h_box = 0.9
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 4, h_box, 'DESCENT PHASE\nSegment Loop: 0-33%, 33-67%, 67-100%', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap)
y_pos = y_bottom - gap

# Start movement (h=0.8)
h_box = 0.8
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 3.2, h_box, 'Start Movement\nat Current Tier Speed', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap)
y_pos = y_bottom - gap

# Monitor force loop (h=0.7)
h_box = 0.7
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 2.8, h_box, 'Monitor Force\nEvery 20ms', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap)
y_pos = y_bottom - gap

# Force check 1 (diamond)
h_diamond = 1.6
y_pos -= h_diamond/2
y_pos_adaptive_branch = y_pos  # Save this position for adaptive branch
draw_diamond(ax, x_main, y_pos, 1.6, 1.6, 'Force ≤\n75%\nThreshold?', color_decision)
draw_arrow(ax, x_main + 0.9, y_pos, x_adapt, y_pos, 'YES')
y_bottom = y_pos - h_diamond/2 - 0.3
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap, 'NO')
y_pos = y_bottom - gap

# Reached target check (diamond)
h_diamond = 1.5
y_pos -= h_diamond/2
draw_diamond(ax, x_main, y_pos, 1.5, 1.5, 'Reached\nSegment\nTarget?', color_decision)
# Loop back arrow (left side)
x_loop = 4.5
y_loop_target = y_pos - 8
draw_arrow(ax, x_main - 1.0, y_pos, x_loop, y_pos)
draw_arrow(ax, x_loop, y_pos, x_loop, y_loop_target)
draw_arrow(ax, x_loop, y_loop_target, x_main, y_loop_target, 'NO\n(Next Seg)')
y_bottom = y_pos - h_diamond/2 - 0.3
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap, 'YES')
y_pos = y_bottom - gap

# Reached glass check (diamond)
h_diamond = 1.5
y_pos -= h_diamond/2
draw_diamond(ax, x_main, y_pos, 1.5, 1.5, 'Reached\nGlass\nPosition?', color_decision)
# YES path - skip to speed check
y_speed_check_pos = y_pos_adaptive_branch - 16
draw_arrow(ax, x_main + 0.8, y_pos, x_adapt - 0.5, y_pos, 'YES')
draw_arrow(ax, x_adapt - 0.5, y_pos, x_adapt - 0.5, y_speed_check_pos)
# NO path - continue loop
y_bottom = y_pos - h_diamond/2 - 0.3
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - 0.5, 'NO')
draw_arrow(ax, x_main, y_bottom - 0.5, x_loop, y_bottom - 0.8)
draw_arrow(ax, x_loop, y_bottom - 0.8, x_loop, y_loop_target, 'Continue\nLoop')
y_pos = y_bottom - 1.5

# === ADAPTIVE STOP PATH (right side) ===
y_adapt = y_pos_adaptive_branch
gap_adapt = 0.7

# STOP STAGE (h=0.7)
h_box = 0.7
y_adapt -= h_box/2 + gap_adapt
draw_box(ax, x_adapt, y_adapt, 1.6, h_box, '*** STOP\nSTAGE ***', color_adaptive)
y_bottom = y_adapt - h_box/2
draw_arrow(ax, x_adapt, y_bottom, x_adapt, y_bottom - gap_adapt)
y_adapt = y_bottom - gap_adapt

# WAIT (h=0.8)
h_box = 0.8
y_adapt -= h_box/2
draw_box(ax, x_adapt, y_adapt, 1.8, h_box, 'WAIT:\nForce ≥ 50%\nOR 3 seconds', color_adaptive)
y_bottom = y_adapt - h_box/2
draw_arrow(ax, x_adapt, y_bottom, x_adapt, y_bottom - gap_adapt)
y_adapt = y_bottom - gap_adapt

# REDUCE SPEED (h=0.8)
h_box = 0.8
y_adapt -= h_box/2
draw_box(ax, x_adapt, y_adapt, 1.9, h_box, 'REDUCE SPEED\nSpeed = Speed × 0.5\nFlag: speed_reduced', color_adaptive)
y_bottom = y_adapt - h_box/2
draw_arrow(ax, x_adapt, y_bottom, x_adapt, y_bottom - gap_adapt)
y_adapt = y_bottom - gap_adapt

# Resume movement (h=0.7)
h_box = 0.7
y_adapt -= h_box/2
draw_box(ax, x_adapt, y_adapt, 1.9, h_box, 'Resume to\nSegment Target\nat Reduced Speed', color_adaptive)
y_bottom = y_adapt - h_box/2
draw_arrow(ax, x_adapt, y_bottom, x_adapt, y_bottom - 1.2)
y_adapt = y_bottom - 1.2

# Loop back to monitor
draw_arrow(ax, x_adapt, y_adapt, x_adapt, y_adapt - 1.5)
draw_arrow(ax, x_adapt, y_adapt - 1.5, x_main, y_adapt - 1.5)

# === SPEED ADAPTATION CHECK (at glass) ===
y_pos = y_speed_check_pos
h_diamond = 1.5
draw_diamond(ax, x_adapt - 0.5, y_pos, 1.5, 1.5, 'Speed\nWas\nReduced?', color_decision)
y_bottom = y_pos - h_diamond/2 - 0.3
draw_arrow(ax, x_adapt - 0.5, y_bottom, x_adapt - 0.5, y_bottom - gap, 'YES')
y_pos = y_bottom - gap

# REDEFINE SPEEDS (h=1.0)
h_box = 1.0
y_pos -= h_box/2
draw_box(ax, x_adapt - 0.5, y_pos, 2.3, h_box, 'REDEFINE SPEEDS\nfor ALL Future Layers:\nNew Base = Final Tier3 × 9', color_adaptive)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_adapt - 0.5, y_bottom, x_adapt - 0.5, y_bottom - gap)
# NO path
draw_arrow(ax, x_adapt - 1.2, y_speed_check_pos, x_main, y_speed_check_pos, 'NO')
y_pos = y_bottom - gap

# Convergence point
y_converge = y_pos
draw_arrow(ax, x_adapt - 0.5, y_converge, x_main, y_converge)
draw_arrow(ax, x_main, y_speed_check_pos, x_main, y_converge)
y_pos = y_converge - gap

# === ASCENT PHASE ===
h_box = 0.8
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 3.5, h_box, 'ASCENT PHASE\n(Simplified - No Extra Movements)', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap)
y_pos = y_bottom - gap

# Ascent Seg 1 (h=0.7)
h_box = 0.7
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 2.8, h_box, 'Seg 1: 0-33%\nat Tier3 (slowest)', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap*0.7)
y_pos = y_bottom - gap*0.7

# Ascent Seg 2 (h=0.7)
h_box = 0.7
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 2.8, h_box, 'Seg 2: 33-50%\nat Tier2', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap*0.7)
y_pos = y_bottom - gap*0.7

# PAUSE (h=0.7)
h_box = 0.7
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 2.3, h_box, '*** PAUSE 3s ***\nat 50% Point', color_adaptive)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap*0.7)
y_pos = y_bottom - gap*0.7

# Ascent Seg 3 (h=0.7)
h_box = 0.7
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 2.8, h_box, 'Seg 3: 50-100%\nat Tier1 (fastest)', color_process)
y_bottom = y_pos - h_box/2
draw_arrow(ax, x_main, y_bottom, x_main, y_bottom - gap*0.7)
y_pos = y_bottom - gap*0.7

# COMPLETE (h=0.8)
h_box = 0.8
y_pos -= h_box/2
draw_box(ax, x_main, y_pos, 3, h_box, 'SANDWICH COMPLETE\nContinue to Exposure', color_complete)

# Add title and legend
ax.text(6, 39.2, 'ADAPTIVE SANDWICH ROUTINE FLOWCHART', 
        fontsize=18, weight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', edgecolor='black', linewidth=2))

# Legend
legend_elements = [
    mpatches.Patch(facecolor=color_start, edgecolor='black', label='Start/End'),
    mpatches.Patch(facecolor=color_process, edgecolor='black', label='Process'),
    mpatches.Patch(facecolor=color_decision, edgecolor='black', label='Decision'),
    mpatches.Patch(facecolor=color_adaptive, edgecolor='black', label='Adaptive Action'),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=11)

# Add key parameters box
param_text = (
    "KEY PARAMETERS:\n"
    "• 3-Tier Ramping: Base, Base÷3, Base÷9\n"
    "• Adaptive Threshold: 75% of max force\n"
    "• Relaxation Target: 50% of max force\n"
    "• Wait Timeout: 3 seconds\n"
    "• Speed Reduction: 50% per trigger\n"
    "• Future Layer Adjustment: Base = FinalTier3 × 9"
)
ax.text(1, 3, param_text, fontsize=9, family='monospace',
        bbox=dict(boxstyle='round,pad=0.8', facecolor='lightyellow', 
                  edgecolor='black', linewidth=1.5, alpha=0.95))

plt.tight_layout()
plt.savefig('adaptive_sandwich_flowchart.png', dpi=300, bbox_inches='tight')
print("Flowchart saved as: adaptive_sandwich_flowchart.png")
plt.close()
