import pandas as pd
import os
os.chdir(r"C:\Users\Bologna\Desktop\anaconda")

os.makedirs("images", exist_ok=True)

header = pd.read_csv("euroleague_header.csv")

box_score = pd.read_csv("euroleague_box_score.csv")
print(box_score.shape)
print(box_score.columns.tolist())
print(box_score.head())


comparison = pd.read_csv("euroleague_comparison.csv")
print(comparison.shape)
print(comparison.columns.tolist())
print(comparison.head())

print(comparison[['game_id', 'game', 'team_id_a', 'team_id_b']].head(10))


# ============================================================
# 1. Aggregate box_score to team level (sum across players per game)
# ============================================================

team_box = box_score.groupby(['game_id', 'team_id']).agg(
    offensive_rebounds=('offensive_rebounds', 'sum'),
    defensive_rebounds=('defensive_rebounds', 'sum'),
    steals=('steals', 'sum'),
    blocks_favour=('blocks_favour', 'sum'),
    free_throws_attempted=('free_throws_attempted', 'sum'),
    fouls_received=('fouls_received', 'sum')
).reset_index()

print(team_box.shape)
print(team_box.head())


# ============================================================
# 2. Reshape comparison.csv from wide (a/b) to long (one row per team per game)
# ============================================================

comparison_a = comparison[['game_id', 'team_id_a', 'fast_break_points_a', 'second_chance_points_a']].rename(
    columns={'team_id_a': 'team_id', 'fast_break_points_a': 'fast_break_points', 'second_chance_points_a': 'second_chance_points'}
)

comparison_b = comparison[['game_id', 'team_id_b', 'fast_break_points_b', 'second_chance_points_b']].rename(
    columns={'team_id_b': 'team_id', 'fast_break_points_b': 'fast_break_points', 'second_chance_points_b': 'second_chance_points'}
)

comparison_long = pd.concat([comparison_a, comparison_b], ignore_index=True)

print(comparison_long.shape)
print(comparison_long.head())

# Check if fast_break_points and second_chance_points look real for recent seasons
recent_check = comparison[comparison['season_code'].isin(['E2023', 'E2024', 'E2025'])]
print(recent_check[['season_code', 'fast_break_points_a', 'second_chance_points_a']].describe())

# ============================================================
# 3. Merge box score stats with comparison stats (fast break, 2nd chance)
# ============================================================

team_stats_full = team_box.merge(
    comparison_long,
    on=['game_id', 'team_id'],
    how='left'
)

print(team_stats_full.shape)
print(team_stats_full.head())

# ============================================================
# 4. Add season_code, venue (home/away), and filter for Zalgiris
# ============================================================

# Get season_code and venue info from header.csv (same approach as the Olympiacos project)
header_info = header[['game_id', 'season_code', 'team_id_a', 'team_id_b']].copy()

team_stats_full = team_stats_full.merge(header_info, on='game_id', how='left')

team_stats_full['venue'] = team_stats_full.apply(
    lambda row: 'Home' if row['team_id'] == row['team_id_a'] else 'Away', axis=1
)

# Filter: Zalgiris (ZAL), last 3 seasons
zal_stats = team_stats_full[
    (team_stats_full['team_id'] == 'ZAL') &
    (team_stats_full['season_code'].isin(['E2023', 'E2024', 'E2025']))
].copy()

print(f"\nZalgiris games found (last 3 seasons): {len(zal_stats)}")
print(zal_stats[['game_id', 'season_code', 'venue', 'offensive_rebounds', 'steals', 'fast_break_points']].head(10))

# ============================================================
# 5. Home vs Away comparison — average per game
# ============================================================

stat_columns = [
    'offensive_rebounds', 'defensive_rebounds', 'steals', 'blocks_favour',
    'free_throws_attempted', 'fouls_received', 'fast_break_points', 'second_chance_points'
]

venue_avg = zal_stats.groupby('venue')[stat_columns].mean().round(1)
print(venue_avg)

# Also show it transposed for easier reading (stats as rows, venue as columns)
print("\n=== Transposed for readability ===")
print(venue_avg.T)


# ============================================================
# 6. Bar chart: % difference Home vs Away, for each stat
# ============================================================

import matplotlib.pyplot as plt

pct_diff = ((venue_avg.loc['Home'] - venue_avg.loc['Away']) / venue_avg.loc['Away'] * 100).round(1)
pct_diff = pct_diff.sort_values()

# Readable labels
labels = {
    'offensive_rebounds': 'Offensive rebounds',
    'defensive_rebounds': 'Defensive rebounds',
    'steals': 'Steals',
    'blocks_favour': 'Blocks',
    'free_throws_attempted': 'Free throws attempted',
    'fouls_received': 'Fouls received',
    'fast_break_points': 'Fast break points',
    'second_chance_points': 'Second chance points'
}
pct_diff.index = [labels[i] for i in pct_diff.index]

BG_COLOR = '#0a1f3d'
POSITIVE_COLOR = '#90EE90'
NEGATIVE_COLOR = '#FF7F7F'

fig, ax = plt.subplots(figsize=(9, 6.5))
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)

colors = [POSITIVE_COLOR if v >= 0 else NEGATIVE_COLOR for v in pct_diff]
bars = ax.barh(pct_diff.index, pct_diff.values, color=colors)

ax.axvline(0, color='white', linewidth=0.8)
ax.set_xlabel('% difference, Home vs Away', color='white')
ax.set_title('Zalgiris Kaunas: home court effort impact\n(last 3 seasons)', color='white')

ax.tick_params(colors='white')
for spine in ax.spines.values():
    spine.set_color('white')

# Give extra room on both sides so labels never collide with bars or axis ticks
max_abs = pct_diff.abs().max()
ax.set_xlim(pct_diff.min() - max_abs * 0.35, pct_diff.max() + max_abs * 0.35)

for bar, val in zip(bars, pct_diff.values):
    offset = max_abs * 0.04
    x_pos = val + offset if val >= 0 else val - offset
    ha = 'left' if val >= 0 else 'right'
    ax.text(x_pos, bar.get_y() + bar.get_height()/2, f'{val:+.1f}%', va='center', ha=ha, color='white', fontweight='bold')

plt.tight_layout()
plt.savefig('images/zalgiris_home_away_pct_diff.png', dpi=150, facecolor=fig.get_facecolor(), pad_inches=0.3)
plt.show()

# ============================================================
# 7. Trend over time: Home vs Away, broken down by season
# ============================================================

season_venue_avg = zal_stats.groupby(['season_code', 'venue'])[stat_columns].mean().round(1)
print(season_venue_avg)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(season_venue_avg)

##############################################################

COURT_LINE_COLOR = '#FFD580'

####################################################

game_counts = zal_stats.groupby(['season_code', 'venue']).size()
print(game_counts)

# Check data availability across all seasons for the key advanced stats
availability_check = comparison.groupby('season_code').agg(
    avg_fast_break=('fast_break_points_a', 'mean'),
    avg_second_chance=('second_chance_points_a', 'mean')
).round(1)

print(availability_check)

# ============================================================
# Extend to 2015-2025, now that we know data is reliable from E2015
# ============================================================

seasons_range = [f'E{y}' for y in range(2015, 2026)]

zal_stats_long = team_stats_full[
    (team_stats_full['team_id'] == 'ZAL') &
    (team_stats_full['season_code'].isin(seasons_range))
].copy()

print(f"Zalgiris games found (2015-2025): {len(zal_stats_long)}")

game_counts_long = zal_stats_long.groupby(['season_code', 'venue']).size().unstack()
print(game_counts_long)

###############################################################################

import matplotlib.pyplot as plt

# ============================================================
# League average per season, across all teams (not split by venue)
# ============================================================

league_trend = team_stats_full[
    team_stats_full['season_code'].isin(seasons_range)
].groupby('season_code')[stat_columns].mean().reset_index()

# ============================================================
# Zalgiris trend, split by venue (already computed earlier as trend_data_long)
# ============================================================

trend_data_long = zal_stats_long.groupby(['season_code', 'venue'])[stat_columns].mean().reset_index()

stats_to_plot = ['offensive_rebounds', 'blocks_favour', 'second_chance_points', 'fast_break_points']
titles_map = {
    'offensive_rebounds': 'Offensive rebounds',
    'blocks_favour': 'Blocks',
    'second_chance_points': 'Second chance points',
    'fast_break_points': 'Fast break points'
}

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.patch.set_facecolor(BG_COLOR)

for ax, stat in zip(axes.flat, stats_to_plot):
    ax.set_facecolor(BG_COLOR)

    for venue_type, color in zip(['Home', 'Away'], [POSITIVE_COLOR, COURT_LINE_COLOR]):
        subset = trend_data_long[trend_data_long['venue'] == venue_type]
        ax.plot(subset['season_code'], subset[stat], marker='o', color=color, label=f'Zalgiris {venue_type}', linewidth=2)

    # League average, overlaid in white, dashed, slightly thinner
    ax.plot(league_trend['season_code'], league_trend[stat], marker='s', color='white',
            label='EuroLeague avg', linewidth=1.5, linestyle='--', alpha=0.8, markersize=5)

    ax.set_title(titles_map[stat], color='white')
    ax.tick_params(colors='white', rotation=45)
    for spine in ax.spines.values():
        spine.set_color('white')
    ax.legend(facecolor=BG_COLOR, edgecolor='white', labelcolor='white', fontsize=9)

plt.tight_layout()
plt.savefig('images/zalgiris_league_trend_2015_2025.png', dpi=150, facecolor=fig.get_facecolor(), pad_inches=0.3)
plt.show()
##############################################################################

league_avg = comparison[comparison['season_code'].isin(seasons_range)].groupby('season_code').agg(
    league_avg_fast_break=('fast_break_points_a', 'mean')
).round(1)
print(league_avg)

sample_2015 = comparison[comparison['season_code'] == 'E2015']
print(sample_2015['fast_break_points_a'].describe())