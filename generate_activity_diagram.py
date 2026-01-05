"""
Script untuk generate Activity Diagram proses scanning file
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Setup figure
fig, ax = plt.subplots(1, 1, figsize=(10, 14))
ax.set_xlim(0, 10)
ax.set_ylim(0, 20)
ax.axis('off')

# Colors - Black and White theme
start_end_color = '#E8E8E8'  # Light gray
process_color = '#FFFFFF'    # White
decision_color = '#E8E8E8'   # Light gray
alert_color = '#FFFFFF'      # White
safe_color = '#E8E8E8'       # Light gray

# Helper function to draw rounded rectangle
def draw_process(ax, x, y, width, height, text, color):
    box = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.1",
                         edgecolor='black', facecolor=color, linewidth=2)
    ax.add_patch(box)
    ax.text(x + width/2, y + height/2, text, ha='center', va='center',
            fontsize=10, fontweight='normal', color='black', wrap=True)

# Helper function to draw diamond (decision)
def draw_decision(ax, x, y, size, text, color):
    diamond = patches.FancyBboxPatch((x-size/2, y-size/2), size, size,
                                     boxstyle="round,pad=0.05",
                                     transform=ax.transData,
                                     edgecolor='black', facecolor=color, linewidth=2)
    # Rotate to make diamond
    t = plt.matplotlib.transforms.Affine2D().rotate_deg_around(x, y, 45) + ax.transData
    diamond.set_transform(t)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center',
            fontsize=9, fontweight='normal', color='black')

# Helper function to draw arrow
def draw_arrow(ax, x1, y1, x2, y2, label=''):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                           arrowstyle='->', mutation_scale=20, linewidth=2,
                           color='black')
    ax.add_patch(arrow)
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x + 0.5, mid_y, label, fontsize=9, color='black',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# Helper function to draw circle (start/end)
def draw_circle(ax, x, y, radius, text, color):
    circle = patches.Circle((x, y), radius, edgecolor='black',
                           facecolor=color, linewidth=2)
    ax.add_patch(circle)
    ax.text(x, y, text, ha='center', va='center',
            fontsize=9, fontweight='normal', color='black')

# Draw activity diagram elements
y_pos = 19

# Start
draw_circle(ax, 5, y_pos, 0.4, 'Start', start_end_color)
y_pos -= 1.5

# Pengguna memilih file
draw_arrow(ax, 5, y_pos + 1.1, 5, y_pos + 0.6)
draw_process(ax, 3.5, y_pos - 0.6, 3, 1, 'User Memilih\nFile untuk Scan', process_color)
y_pos -= 2

# Loading model ONNX
draw_arrow(ax, 5, y_pos + 1.4, 5, y_pos + 0.6)
draw_process(ax, 3.5, y_pos - 0.6, 3, 1, 'Loading\nONNX Model', process_color)
y_pos -= 2

# Konversi file ke gambar
draw_arrow(ax, 5, y_pos + 1.4, 5, y_pos + 0.6)
draw_process(ax, 3.5, y_pos - 0.6, 3, 1, 'Konversi File ke\nImage Representation', process_color)
y_pos -= 2

# Preprocessing
draw_arrow(ax, 5, y_pos + 1.4, 5, y_pos + 0.6)
draw_process(ax, 3.5, y_pos - 0.6, 3, 1, 'Preprocessing\n(Resize & Format)', process_color)
y_pos -= 2

# Inferensi AI
draw_arrow(ax, 5, y_pos + 1.4, 5, y_pos + 0.6)
draw_process(ax, 3.5, y_pos - 0.6, 3, 1, 'Inferensi AI\n(Prediction)', process_color)
y_pos -= 2

# Decision: Malware detected?
draw_arrow(ax, 5, y_pos + 1.4, 5, y_pos + 0.8)
draw_decision(ax, 5, y_pos, 1.2, 'Malware\nDetected?', decision_color)
y_pos -= 2

# Yes - Show alert
draw_arrow(ax, 5 - 0.85, y_pos + 1.15, 2.5, y_pos + 0.5, label='Ya')
draw_process(ax, 0.8, y_pos - 0.6, 3, 1, 'Tampilkan\nMalware Alert', alert_color)
alert_y = y_pos

# No - Show benign
draw_arrow(ax, 5 + 0.85, y_pos + 1.15, 7.5, y_pos + 0.5, label='Tidak')
draw_process(ax, 6.2, y_pos - 0.6, 3, 1, 'Tampilkan\nStatus Benign', safe_color)
benign_y = y_pos

y_pos -= 2.5

# Arrows from both paths to save to database
draw_arrow(ax, 2.3, alert_y - 0.6, 5, y_pos + 0.6)
draw_arrow(ax, 7.7, benign_y - 0.6, 5, y_pos + 0.6)

# Save to database
draw_process(ax, 3.5, y_pos - 0.6, 3, 1, 'Simpan Hasil Scan\nke Database', process_color)
y_pos -= 2

# End
draw_arrow(ax, 5, y_pos + 1.4, 5, y_pos + 0.8)
draw_circle(ax, 5, y_pos, 0.4, 'End', start_end_color)

# Title
plt.title('Activity Diagram - Proses Scanning File Malware\nMangoDefend Desktop Application',
          fontsize=14, fontweight='bold', pad=20)

# Save
plt.tight_layout()
plt.savefig('activity_diagram_scanning.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Activity diagram berhasil dibuat: activity_diagram_scanning.png")
plt.close()
