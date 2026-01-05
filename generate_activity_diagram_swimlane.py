"""
Script untuk generate Activity Diagram dengan Swimlane untuk proses scanning file
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import numpy as np

# Setup figure
fig, ax = plt.subplots(1, 1, figsize=(13, 16))
ax.set_xlim(0, 13)
ax.set_ylim(0, 17)
ax.axis('off')

# Define swimlane columns
col1_x = 0.3
col1_width = 3.5
col2_x = col1_x + col1_width
col2_width = 5.5
col3_x = col2_x + col2_width
col3_width = 3.7

# Colors
bg_color = '#FFFFFF'
border_color = '#000000'
shape_color = '#FFFFFF'
text_color = '#000000'
filled_color = '#000000'

# Draw title
ax.text(6.5, 16.5, 'File Scanning Activity Diagram', ha='center', va='center',
        fontsize=13, fontweight='bold', color=text_color)

# Draw swimlane headers
header_height = 16
header_y = header_height - 0.5

# Header backgrounds
ax.add_patch(patches.Rectangle((col1_x, header_y), col1_width, 0.5, 
                               edgecolor=border_color, facecolor='#F0F0F0', linewidth=2))
ax.add_patch(patches.Rectangle((col2_x, header_y), col2_width, 0.5,
                               edgecolor=border_color, facecolor='#F0F0F0', linewidth=2))
ax.add_patch(patches.Rectangle((col3_x, header_y), col3_width, 0.5,
                               edgecolor=border_color, facecolor='#F0F0F0', linewidth=2))

# Header text
ax.text(col1_x + col1_width/2, header_y + 0.25, 'User', ha='center', va='center',
        fontsize=10, fontweight='bold', color=text_color)
ax.text(col2_x + col2_width/2, header_y + 0.25, 'Desktop Application', ha='center', va='center',
        fontsize=10, fontweight='bold', color=text_color)
ax.text(col3_x + col3_width/2, header_y + 0.25, 'AI Model', ha='center', va='center',
        fontsize=10, fontweight='bold', color=text_color)

# Draw swimlane vertical lines
ax.plot([col1_x, col1_x], [0.5, header_y], color=border_color, linewidth=2)
ax.plot([col2_x, col2_x], [0.5, header_y], color=border_color, linewidth=2)
ax.plot([col3_x, col3_x], [0.5, header_y], color=border_color, linewidth=2)
ax.plot([col3_x + col3_width, col3_x + col3_width], [0.5, header_y], color=border_color, linewidth=2)

# Draw bottom line
ax.plot([col1_x, col3_x + col3_width], [0.5, 0.5], color=border_color, linewidth=2)

# Helper functions
def draw_circle(ax, x, y, radius, filled=True):
    if filled:
        circle = Circle((x, y), radius, edgecolor=border_color, 
                       facecolor=filled_color, linewidth=2)
    else:
        circle = Circle((x, y), radius, edgecolor=border_color, 
                       facecolor=bg_color, linewidth=2)
        inner_circle = Circle((x, y), radius*0.6, edgecolor='none', 
                             facecolor=filled_color, linewidth=0)
        ax.add_patch(inner_circle)
    ax.add_patch(circle)

def draw_process(ax, x, y, width, height, text):
    box = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.04",
                         edgecolor=border_color, facecolor=shape_color, linewidth=1.5)
    ax.add_patch(box)
    # Split text for better formatting
    lines = text.split('\n')
    if len(lines) > 2:
        ax.text(x + width/2, y + height/2, text, ha='center', va='center',
                fontsize=8.5, color=text_color, linespacing=1.3)
    else:
        ax.text(x + width/2, y + height/2, text, ha='center', va='center',
                fontsize=9, color=text_color, linespacing=1.3)

def draw_diamond(ax, x, y, width, height, text):
    diamond_points = np.array([
        [x, y + height/2],
        [x + width/2, y + height],
        [x + width, y + height/2],
        [x + width/2, y]
    ])
    diamond = patches.Polygon(diamond_points, closed=True,
                             edgecolor=border_color, facecolor=shape_color, linewidth=1.5)
    ax.add_patch(diamond)
    ax.text(x + width/2, y + height/2, text, ha='center', va='center',
            fontsize=8, color=text_color)

def draw_arrow(ax, x1, y1, x2, y2, label='', label_offset=0.3):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                           arrowstyle='->', mutation_scale=15, linewidth=1.5,
                           color=border_color)
    ax.add_patch(arrow)
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x, mid_y + label_offset, label, fontsize=8, color=text_color,
                ha='center', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                      edgecolor='none'))

# Start drawing the flow
y_pos = 15

# 1. Start (filled circle) - User column
start_x = col1_x + col1_width/2
draw_circle(ax, start_x, y_pos, 0.22, filled=True)
y_pos -= 0.8

# 2. Memilih File - User column
draw_arrow(ax, start_x, y_pos + 0.58, start_x, y_pos + 0.4)
process1_x = col1_x + 0.4
process_width = col1_width - 0.8
draw_process(ax, process1_x, y_pos - 0.4, process_width, 0.7, 'Memilih File\nuntuk Scan')
y_pos -= 1.3

# 3. Arrow to Desktop App
draw_arrow(ax, start_x, y_pos + 0.5, col2_x + col2_width/2, y_pos + 0.5)
y_pos -= 0.4

# 4. Loading Model - Desktop App column
app_x = col2_x + 0.6
app_width = col2_width - 1.2
draw_process(ax, app_x, y_pos - 0.4, app_width, 0.7, 'Loading\nONNX Model')
y_pos -= 1.3

# 5. Konversi File - Desktop App column
draw_arrow(ax, col2_x + col2_width/2, y_pos + 0.6, col2_x + col2_width/2, y_pos + 0.4)
draw_process(ax, app_x, y_pos - 0.4, app_width, 0.7, 'Konversi File ke\nImage Representation')
y_pos -= 1.3

# 6. Preprocessing - Desktop App column
draw_arrow(ax, col2_x + col2_width/2, y_pos + 0.6, col2_x + col2_width/2, y_pos + 0.4)
draw_process(ax, app_x, y_pos - 0.4, app_width, 0.7, 'Preprocessing\n(Resize & Format)')
y_pos -= 1.3

# 7. Arrow to AI Model
draw_arrow(ax, col2_x + col2_width/2, y_pos + 0.6, col3_x + col3_width/2, y_pos + 0.2)
y_pos -= 0.4

# 8. Inferensi AI - AI Model column
model_x = col3_x + 0.4
model_width = col3_width - 0.8
draw_process(ax, model_x, y_pos - 0.4, model_width, 0.7, 'Inferensi AI\n(Prediction)')
y_pos -= 1.3

# 9. Arrow back to Desktop App for decision
draw_arrow(ax, col3_x + col3_width/2, y_pos + 0.6, col2_x + col2_width/2, y_pos + 0.2)
y_pos -= 0.4

# 10. Decision Diamond - Desktop App column
diamond_x = col2_x + col2_width/2 - 0.55
diamond_w = 1.1
diamond_h = 0.8
draw_diamond(ax, diamond_x, y_pos - diamond_h, diamond_w, diamond_h, 'Malware\nDetected?')
decision_center_y = y_pos - diamond_h/2
y_pos -= 1.3

# 11. Yes path - Show Alert
draw_arrow(ax, col2_x + col2_width/2, decision_center_y - diamond_h/2, 
          col2_x + col2_width/2, y_pos + 0.4, label='Yes')
draw_process(ax, app_x, y_pos - 0.4, app_width, 0.7, 'Tampilkan\nMalware Alert')
alert_center_y = y_pos
y_pos_temp = y_pos

# 12. No path - Show Benign (to the right)
no_path_x = col2_x + col2_width - 0.7
draw_arrow(ax, diamond_x + diamond_w, decision_center_y, no_path_x + 0.65, decision_center_y, label='No')
draw_arrow(ax, no_path_x + 0.65, decision_center_y, no_path_x + 0.65, alert_center_y)
draw_process(ax, no_path_x, alert_center_y - 0.4, 1.3, 0.7, 'Tampilkan\nStatus\nBenign')

y_pos = y_pos_temp - 1.3

# 13. Merge paths - Save to Database
draw_arrow(ax, col2_x + col2_width/2, y_pos + 0.6, col2_x + col2_width/2, y_pos + 0.4)
draw_arrow(ax, no_path_x + 0.65, alert_center_y - 0.4, no_path_x + 0.65, y_pos + 0.2)
draw_arrow(ax, no_path_x + 0.65, y_pos + 0.2, col2_x + col2_width/2, y_pos + 0.2)
draw_process(ax, app_x, y_pos - 0.4, app_width, 0.7, 'Simpan Hasil Scan\nke Database')
y_pos -= 1.3

# 14. End (circle with dot) - Desktop App column
draw_arrow(ax, col2_x + col2_width/2, y_pos + 0.6, col2_x + col2_width/2, y_pos + 0.3)
draw_circle(ax, col2_x + col2_width/2, y_pos, 0.22, filled=False)

# Save
plt.tight_layout()
plt.savefig('activity_diagram_scanning.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Activity diagram dengan swimlane berhasil dibuat: activity_diagram_scanning.png")
plt.close()
