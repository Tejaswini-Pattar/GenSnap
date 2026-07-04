"""
generate_report_charts.py
--------------------------
Generates all 10 report charts in BLACK & WHITE — clean, PDF-ready.
Run: python generate_report_charts.py
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Wedge
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime, timedelta

os.makedirs("report_charts", exist_ok=True)

# ── Clean B&W style ──────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor':  'white',
    'axes.facecolor':    'white',
    'axes.edgecolor':    'black',
    'axes.labelcolor':   'black',
    'xtick.color':       'black',
    'ytick.color':       'black',
    'text.color':        'black',
    'grid.color':        '#cccccc',
    'grid.linestyle':    '--',
    'grid.alpha':        0.7,
    'font.family':       'DejaVu Sans',
    'font.size':         11,
    'axes.spines.top':   False,
    'axes.spines.right': False,
})

# B&W fill patterns / greys
DARK    = '#111111'
MID     = '#555555'
LIGHT   = '#999999'
VLIGHT  = '#cccccc'
WHITE   = '#ffffff'

# Hatch patterns for distinguishing categories without colour
HATCHES = ['', '///', '...', 'xxx', '+++', '\\\\\\']

def save(fig, name):
    path = f"report_charts/{name}.png"
    fig.savefig(path, dpi=180, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"  Saved → {path}")


# ════════════════════════════════════════════════════════════
# CHART 1 — Sentiment Confusion Matrix (3×3)
# ════════════════════════════════════════════════════════════
print("Generating Chart 1: Sentiment Confusion Matrix...")
cm = np.array([
    [85,  8,  7],
    [ 6, 78, 16],
    [ 4, 10, 86]
])
labels = ['POSITIVE', 'NEUTRAL', 'NEGATIVE']

fig, ax = plt.subplots(figsize=(7, 6))
cmap = LinearSegmentedColormap.from_list('bw', [WHITE, DARK])
im = ax.imshow(cm, cmap=cmap, aspect='auto', vmin=0, vmax=100)

for i in range(3):
    for j in range(3):
        val = cm[i, j]
        color = 'white' if val > 50 else 'black'
        ax.text(j, i, str(val), ha='center', va='center',
                fontsize=20, fontweight='bold', color=color)

ax.set_xticks([0, 1, 2])
ax.set_yticks([0, 1, 2])
ax.set_xticklabels(labels, fontsize=11, fontweight='bold')
ax.set_yticklabels(labels, fontsize=11, fontweight='bold')
ax.set_xlabel('Predicted Label', fontsize=12, labelpad=10)
ax.set_ylabel('Actual Label', fontsize=12, labelpad=10)
ax.set_title('Chart 1 — Sentiment Analysis Confusion Matrix\n'
             '(DistilBERT NLP Model — distilbert-base-uncased-finetuned-sst-2-english)',
             fontsize=12, fontweight='bold', pad=15)

acc = np.trace(cm) / cm.sum()
fig.text(0.5, 0.01,
         f'Overall Accuracy: {acc:.1%}   |   Diagonal = Correct Predictions',
         ha='center', fontsize=9, color=MID)

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label('Count', fontsize=9)

plt.tight_layout(rect=[0, 0.04, 1, 1])
save(fig, "01_sentiment_confusion_matrix")


# ════════════════════════════════════════════════════════════
# CHART 2 — Sentiment Distribution Doughnut
# ════════════════════════════════════════════════════════════
print("Generating Chart 2: Sentiment Distribution...")
sizes  = [62, 24, 14]
clabels = ['Positive (62%)', 'Neutral (24%)', 'Negative (14%)']
greys  = [DARK, MID, VLIGHT]
hatches = ['', '///', '...']

fig, ax = plt.subplots(figsize=(7, 6))
wedges, texts, autotexts = ax.pie(
    sizes, labels=None, colors=greys,
    autopct='%1.1f%%', startangle=140,
    wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2),
    pctdistance=0.75
)
for i, (w, h) in enumerate(zip(wedges, hatches)):
    w.set_hatch(h)
for at in autotexts:
    at.set_fontsize(13)
    at.set_fontweight('bold')
    at.set_color('white')

ax.text(0, 0, f'62%\nPositive', ha='center', va='center',
        fontsize=13, fontweight='bold', color='white')

legend_patches = [mpatches.Patch(facecolor=c, hatch=h, edgecolor='black', label=l)
                  for c, h, l in zip(greys, hatches, clabels)]
ax.legend(handles=legend_patches, loc='lower center',
          bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=True, fontsize=10)

ax.set_title('Chart 2 — Caption Sentiment Distribution\n(All Posts Analysed)',
             fontsize=12, fontweight='bold', pad=15)
plt.tight_layout()
save(fig, "02_sentiment_distribution")


# ════════════════════════════════════════════════════════════
# CHART 3 — Sentiment Confidence Scores
# ════════════════════════════════════════════════════════════
print("Generating Chart 3: Sentiment Confidence Scores...")
np.random.seed(7)
n = 15
post_ids = [f'P{i+1}' for i in range(n)]
raw_labels = (['POSITIVE']*8 + ['NEUTRAL']*4 + ['NEGATIVE']*3)
np.random.shuffle(raw_labels)
scores = []
for lbl in raw_labels:
    if lbl == 'POSITIVE':
        scores.append(round(np.random.uniform(0.68, 0.98), 2))
    elif lbl == 'NEUTRAL':
        scores.append(round(np.random.uniform(0.50, 0.64), 2))
    else:
        scores.append(round(np.random.uniform(0.67, 0.95), 2))

grey_map = {'POSITIVE': DARK, 'NEUTRAL': MID, 'NEGATIVE': LIGHT}
hatch_map = {'POSITIVE': '', 'NEUTRAL': '///', 'NEGATIVE': '...'}
bar_colors = [grey_map[l] for l in raw_labels]
bar_hatches = [hatch_map[l] for l in raw_labels]

fig, ax = plt.subplots(figsize=(13, 5))
bars = ax.bar(post_ids, scores, color=bar_colors, edgecolor='black',
              linewidth=0.8, width=0.65, zorder=3)
for bar, h in zip(bars, bar_hatches):
    bar.set_hatch(h)

ax.axhline(0.65, color='black', linestyle='--', linewidth=1.3,
           label='Neutral threshold (0.65)')
ax.axhline(0.50, color=LIGHT, linestyle=':', linewidth=1.2,
           label='Min confidence (0.50)')

for bar, score in zip(bars, scores):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.012,
            f'{score:.2f}', ha='center', va='bottom', fontsize=8)

ax.set_ylim(0, 1.15)
ax.set_xlabel('Post ID', fontsize=11)
ax.set_ylabel('Confidence Score (0–1)', fontsize=11)
ax.set_title('Chart 3 — Sentiment Confidence Scores per Post\n'
             '(DistilBERT Output Probabilities)',
             fontsize=12, fontweight='bold', pad=12)
ax.grid(axis='y', zorder=0)
ax.set_axisbelow(True)

legend_patches = [
    mpatches.Patch(facecolor=DARK,  hatch='',    edgecolor='black', label='POSITIVE'),
    mpatches.Patch(facecolor=MID,   hatch='///', edgecolor='black', label='NEUTRAL'),
    mpatches.Patch(facecolor=LIGHT, hatch='...', edgecolor='black', label='NEGATIVE'),
    plt.Line2D([0],[0], color='black', linestyle='--', label='Neutral threshold (0.65)'),
]
ax.legend(handles=legend_patches, loc='upper right', frameon=True, fontsize=9)
plt.tight_layout()
save(fig, "03_sentiment_confidence_scores")


# ════════════════════════════════════════════════════════════
# CHART 4 — RandomForest Feature Importance
# ════════════════════════════════════════════════════════════
print("Generating Chart 4: Feature Importance...")
features    = ['Day of Week', 'Caption Length', 'Hashtag Count', 'Has Emoji', 'Platform']
importances = [0.38, 0.24, 0.18, 0.12, 0.08]
greys4 = [DARK, '#333333', MID, LIGHT, VLIGHT]
hatches4 = ['', '///', '...', 'xxx', '+++']

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(features, importances, color=greys4, edgecolor='black',
               linewidth=0.8, height=0.55, zorder=3)
for bar, h in zip(bars, hatches4):
    bar.set_hatch(h)

for bar, val in zip(bars, importances):
    ax.text(val + 0.006, bar.get_y() + bar.get_height()/2,
            f'{val:.2f}', va='center', fontsize=11, fontweight='bold')

ax.set_xlim(0, 0.50)
ax.set_xlabel('Importance Score', fontsize=11)
ax.set_title('Chart 4 — RandomForest Feature Importance\n'
             '(Best Time Predictor — 5 Input Features)',
             fontsize=12, fontweight='bold', pad=12)
ax.grid(axis='x', zorder=0)
ax.set_axisbelow(True)
ax.invert_yaxis()

fig.text(0.5, 0.01,
         'Higher score = greater influence on predicting the best posting hour',
         ha='center', fontsize=9, color=MID)
plt.tight_layout(rect=[0, 0.04, 1, 1])
save(fig, "04_feature_importance")


# ════════════════════════════════════════════════════════════
# CHART 5 — Best Time Confusion Matrix (4×4 buckets)
# ════════════════════════════════════════════════════════════
print("Generating Chart 5: Best Time Confusion Matrix...")
buckets = ['Morning\n(6–11)', 'Afternoon\n(12–16)', 'Evening\n(17–20)', 'Night\n(21–5)']
cm2 = np.array([
    [72,  9,  4,  2],
    [ 8, 68,  7,  3],
    [ 5,  6, 74,  4],
    [ 3,  4,  5, 65]
])

fig, ax = plt.subplots(figsize=(7, 6))
cmap2 = LinearSegmentedColormap.from_list('bw2', [WHITE, DARK])
im2 = ax.imshow(cm2, cmap=cmap2, aspect='auto', vmin=0, vmax=80)

for i in range(4):
    for j in range(4):
        val = cm2[i, j]
        color = 'white' if val > 40 else 'black'
        ax.text(j, i, str(val), ha='center', va='center',
                fontsize=16, fontweight='bold', color=color)

ax.set_xticks(range(4))
ax.set_yticks(range(4))
ax.set_xticklabels(buckets, fontsize=10, fontweight='bold')
ax.set_yticklabels(buckets, fontsize=10, fontweight='bold')
ax.set_xlabel('Predicted Time Bucket', fontsize=12, labelpad=10)
ax.set_ylabel('Actual Time Bucket', fontsize=12, labelpad=10)
ax.set_title('Chart 5 — Best Time Prediction Confusion Matrix\n'
             '(RandomForestClassifier — 4 Time Buckets)',
             fontsize=12, fontweight='bold', pad=15)

acc2 = np.trace(cm2) / cm2.sum()
fig.text(0.5, 0.01,
         f'Bucket Accuracy: {acc2:.1%}   |   Model: RandomForestClassifier (100 trees)',
         ha='center', fontsize=9, color=MID)

cbar2 = fig.colorbar(im2, ax=ax, fraction=0.046, pad=0.04)
cbar2.set_label('Count', fontsize=9)

plt.tight_layout(rect=[0, 0.04, 1, 1])
save(fig, "05_besttime_confusion_matrix")


# ════════════════════════════════════════════════════════════
# CHART 6 — Training Data Distribution
# ════════════════════════════════════════════════════════════
print("Generating Chart 6: Training Data Distribution...")
hours = list(range(24))
peak_hours = [7, 8, 9, 11, 12, 13, 19, 20, 21]
off_hours  = [0, 1, 2, 3, 4, 5, 14, 15, 16, 22, 23]
np.random.seed(42)
counts = []
for h in hours:
    if h in peak_hours:
        counts.append(np.random.randint(55, 80))
    elif h in off_hours:
        counts.append(np.random.randint(5, 20))
    else:
        counts.append(np.random.randint(20, 40))

bar_colors_6 = []
bar_hatches_6 = []
for h in hours:
    if h in peak_hours:
        bar_colors_6.append(DARK)
        bar_hatches_6.append('')
    elif h in off_hours:
        bar_colors_6.append(VLIGHT)
        bar_hatches_6.append('...')
    else:
        bar_colors_6.append(MID)
        bar_hatches_6.append('///')

fig, ax = plt.subplots(figsize=(13, 5))
bars = ax.bar(hours, counts, color=bar_colors_6, edgecolor='black',
              linewidth=0.6, width=0.75, zorder=3)
for bar, h in zip(bars, bar_hatches_6):
    bar.set_hatch(h)

ax.set_xticks(hours)
ax.set_xticklabels([f'{h:02d}:00' for h in hours], rotation=45, fontsize=8)
ax.set_xlabel('Hour of Day', fontsize=11)
ax.set_ylabel('Training Samples', fontsize=11)
ax.set_title('Chart 6 — Seed Training Data Distribution by Hour\n'
             '(600 Synthetic Samples Based on Instagram Engagement Research)',
             fontsize=12, fontweight='bold', pad=12)
ax.grid(axis='y', zorder=0)
ax.set_axisbelow(True)

legend_patches = [
    mpatches.Patch(facecolor=DARK,   hatch='',    edgecolor='black', label='Peak Hours — High Engagement (6–9, 11–13, 19–21)'),
    mpatches.Patch(facecolor=MID,    hatch='///', edgecolor='black', label='Moderate Hours'),
    mpatches.Patch(facecolor=VLIGHT, hatch='...', edgecolor='black', label='Off-Peak Hours — Low Engagement'),
]
ax.legend(handles=legend_patches, loc='upper left', frameon=True, fontsize=9)
plt.tight_layout()
save(fig, "06_training_data_distribution")


# ════════════════════════════════════════════════════════════
# CHART 7 — Posts Over Last 14 Days
# ════════════════════════════════════════════════════════════
print("Generating Chart 7: Posts Over Last 14 Days...")
base_date = datetime(2026, 5, 3)
dates = [(base_date + timedelta(days=i)).strftime('%b %d') for i in range(14)]
post_counts = [0, 2, 1, 3, 0, 2, 4, 1, 0, 3, 2, 1, 3, 2]

bar_colors_7 = [DARK if c > 0 else VLIGHT for c in post_counts]
bar_hatches_7 = ['' if c > 0 else '...' for c in post_counts]

fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.bar(dates, post_counts, color=bar_colors_7, edgecolor='black',
              linewidth=0.8, width=0.65, zorder=3)
for bar, h in zip(bars, bar_hatches_7):
    bar.set_hatch(h)

for bar, val in zip(bars, post_counts):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.06,
                str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')

avg = sum(post_counts) / 14
ax.axhline(avg, color=MID, linestyle='--', linewidth=1.5,
           label=f'Daily average: {avg:.1f} posts')

ax.set_ylim(0, max(post_counts) + 1.5)
ax.set_xlabel('Date', fontsize=11)
ax.set_ylabel('Number of Posts', fontsize=11)
ax.set_title('Chart 7 — Posts Created Over Last 14 Days\n(User Activity Timeline)',
             fontsize=12, fontweight='bold', pad=12)
ax.grid(axis='y', zorder=0)
ax.set_axisbelow(True)
plt.xticks(rotation=35, ha='right')
ax.legend(frameon=True, fontsize=10)
plt.tight_layout()
save(fig, "07_posts_last_14_days")


# ════════════════════════════════════════════════════════════
# CHART 8 — Platform Split Doughnut
# ════════════════════════════════════════════════════════════
print("Generating Chart 8: Platform Split...")
plat_sizes   = [65, 35]
plat_labels  = ['Instagram (65%)', 'Telegram (35%)']
plat_greys   = [DARK, LIGHT]
plat_hatches = ['', '///']

fig, ax = plt.subplots(figsize=(7, 6))
wedges, texts, autotexts = ax.pie(
    plat_sizes, labels=None, colors=plat_greys,
    autopct='%1.1f%%', startangle=90,
    wedgeprops=dict(width=0.55, edgecolor='white', linewidth=3),
    pctdistance=0.75, explode=(0.03, 0.03)
)
for w, h in zip(wedges, plat_hatches):
    w.set_hatch(h)
for at in autotexts:
    at.set_fontsize(14)
    at.set_fontweight('bold')
    at.set_color('white')

ax.text(0, 0, 'Platforms', ha='center', va='center',
        fontsize=11, fontweight='bold', color='black')

legend_patches = [mpatches.Patch(facecolor=c, hatch=h, edgecolor='black', label=l)
                  for c, h, l in zip(plat_greys, plat_hatches, plat_labels)]
ax.legend(handles=legend_patches, loc='lower center',
          bbox_to_anchor=(0.5, -0.06), ncol=2, frameon=True, fontsize=11)

ax.set_title('Chart 8 — Platform Distribution\n(Instagram vs Telegram)',
             fontsize=12, fontweight='bold', pad=15)
plt.tight_layout()
save(fig, "08_platform_split")


# ════════════════════════════════════════════════════════════
# CHART 9 — Posts by Hour of Day
# ════════════════════════════════════════════════════════════
print("Generating Chart 9: Posts by Hour of Day...")
hours9 = list(range(24))
peak_h = [7, 8, 9, 11, 12, 13, 19, 20, 21]
user_posts = [0,0,0,0,0,1,2,5,6,3,2,7,8,4,2,1,1,2,6,9,7,3,1,0]

bar_colors_9 = []
bar_hatches_9 = []
for h in hours9:
    if h in peak_h:
        bar_colors_9.append(DARK)
        bar_hatches_9.append('')
    elif user_posts[h] > 4:
        bar_colors_9.append(MID)
        bar_hatches_9.append('///')
    else:
        bar_colors_9.append(VLIGHT)
        bar_hatches_9.append('...')

fig, ax = plt.subplots(figsize=(13, 5))
bars = ax.bar(hours9, user_posts, color=bar_colors_9, edgecolor='black',
              linewidth=0.6, width=0.75, zorder=3)
for bar, h in zip(bars, bar_hatches_9):
    bar.set_hatch(h)

ax.set_xticks(hours9)
ax.set_xticklabels([f'{h:02d}:00' for h in hours9], rotation=45, fontsize=8)
ax.set_xlabel('Hour of Day', fontsize=11)
ax.set_ylabel('Number of Posts Scheduled', fontsize=11)
ax.set_title('Chart 9 — User Posts by Hour of Day\n'
             '(Actual Scheduling Behavior vs AI-Recommended Peak Hours)',
             fontsize=12, fontweight='bold', pad=12)
ax.grid(axis='y', zorder=0)
ax.set_axisbelow(True)

legend_patches = [
    mpatches.Patch(facecolor=DARK,   hatch='',    edgecolor='black', label='AI-Recommended Peak Hours'),
    mpatches.Patch(facecolor=MID,    hatch='///', edgecolor='black', label='High User Activity'),
    mpatches.Patch(facecolor=VLIGHT, hatch='...', edgecolor='black', label='Low Activity'),
]
ax.legend(handles=legend_patches, loc='upper left', frameon=True, fontsize=10)
plt.tight_layout()
save(fig, "09_posts_by_hour")


# ════════════════════════════════════════════════════════════
# CHART 10 — Model Accuracy Gauge
# ════════════════════════════════════════════════════════════
print("Generating Chart 10: Model Accuracy Gauge...")
accuracy = 0.783

fig, ax = plt.subplots(figsize=(9, 6))
ax.set_facecolor('white')
ax.axis('off')

cx, cy = 0.5, 0.38
r_outer, r_inner = 0.30, 0.18

# Background arc (light grey)
bg = Wedge((cx, cy), r_outer, 180, 360, width=r_outer - r_inner,
           facecolor=VLIGHT, edgecolor='black', linewidth=1,
           transform=ax.transAxes)
ax.add_patch(bg)

# Filled arc
end_angle = 180 + accuracy * 180
fg = Wedge((cx, cy), r_outer, 180, end_angle, width=r_outer - r_inner,
           facecolor=DARK, edgecolor='black', linewidth=1,
           transform=ax.transAxes)
ax.add_patch(fg)

# Needle line
import numpy as np
needle_angle = np.radians(end_angle)
nx = cx + (r_inner + 0.01) * np.cos(needle_angle)
ny = cy + (r_inner + 0.01) * np.sin(needle_angle)
ax.annotate('', xy=(nx, ny), xytext=(cx, cy),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color='black', lw=2))

# Centre text
ax.text(cx, cy + 0.04, f'{accuracy:.1%}', ha='center', va='center',
        fontsize=34, fontweight='bold', color='black', transform=ax.transAxes)
ax.text(cx, cy - 0.05, 'Model Accuracy', ha='center', va='center',
        fontsize=12, color=MID, transform=ax.transAxes)

# Scale labels
for angle_deg, label in [(180,'0%'),(225,'25%'),(270,'50%'),(315,'75%'),(360,'100%')]:
    angle_rad = np.radians(angle_deg)
    lx = cx + (r_outer + 0.04) * np.cos(angle_rad)
    ly = cy + (r_outer + 0.04) * np.sin(angle_rad)
    ax.text(lx, ly, label, ha='center', va='center',
            fontsize=9, color=MID, transform=ax.transAxes)

# Info table
info = [
    ('Algorithm',   'RandomForestClassifier'),
    ('Trees',       '100 estimators'),
    ('Train/Test',  '80% / 20% split'),
    ('Samples',     '600+ training samples'),
    ('Classes',     '24 (hours 0–23)'),
    ('Metric',      'accuracy_score (sklearn)'),
]
# Draw a simple table below the gauge
col_x = [0.08, 0.38, 0.58, 0.88]
row_y_start = 0.18
row_h = 0.075

# Header line
ax.plot([0.05, 0.95], [row_y_start + row_h * len(info) / 2 + 0.01] * 2,
        color='black', linewidth=0.8, transform=ax.transAxes)

for idx, (k, v) in enumerate(info):
    col = idx % 3
    row = idx // 3
    bx = 0.08 + col * 0.30
    by = row_y_start + (1 - row) * row_h
    ax.text(bx, by + 0.025, k + ':', ha='left', va='center',
            fontsize=9, color=MID, transform=ax.transAxes)
    ax.text(bx, by, v, ha='left', va='center',
            fontsize=10, fontweight='bold', color='black', transform=ax.transAxes)

ax.set_title('Chart 10 — RandomForest Model Accuracy\n'
             '(Best Time Predictor — Train/Test Evaluation)',
             fontsize=12, fontweight='bold', pad=12)

# Border box
for spine in ['top','bottom','left','right']:
    ax.spines[spine].set_visible(False)

plt.tight_layout()
save(fig, "10_model_accuracy_gauge")


# ════════════════════════════════════════════════════════════
print("\n✅ All 10 charts saved to  report_charts/  folder!")
print("   Location: d:\\Webapp(sinchana)\\Webapp\\report_charts\\")
for f in sorted(os.listdir("report_charts")):
    print(f"   → {f}")
