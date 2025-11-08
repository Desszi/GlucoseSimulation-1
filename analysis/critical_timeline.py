import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

"""
Kritikus események részletes időpont alapú analízise.
LogData.csv alapján minden kritikus eseménynél megmutatja a BG, meal, action értékeket idővonalon.
"""

def identify_critical_events_from_log(df):
    """
    Kritikus események azonosítása LogData.csv-ből.
    
    Returns:
        dict: {'bg_peaks': [(index, bg_value)], 'bg_lows': [(index, bg_value)]}
    """
    if df.empty or 'blood glucose' not in df.columns:
        return {'bg_peaks': [], 'bg_lows': []}
    
    bg_values = df['blood glucose'].values
    
    # Lokális maximumok keresése (tetőpontok)
    peak_events = []
    for i in range(1, len(bg_values) - 1):
        if (bg_values[i] > bg_values[i-1] and 
            bg_values[i] > bg_values[i+1] and 
            bg_values[i] > 160):  # Csak magas értékeknél
            peak_events.append((i, bg_values[i]))
    
    # Lokális minimumok keresése (mélypontok)
    low_events = []
    for i in range(1, len(bg_values) - 1):
        if (bg_values[i] < bg_values[i-1] and 
            bg_values[i] < bg_values[i+1] and 
            bg_values[i] < 100):  # Csak alacsony értékeknél
            low_events.append((i, bg_values[i]))
    
    # Top 5 legmagasabb csúcs és legalacsonyabb mélypont
    peak_events.sort(key=lambda x: x[1], reverse=True)
    low_events.sort(key=lambda x: x[1])
    
    return {
        'bg_peaks': peak_events[:5],
        'bg_lows': low_events[:5]
    }


def plot_critical_event_timeline(df, event_index, event_bg, event_type, window_size=30):
    """
    Egy kritikus esemény körüli időablak részletes ábrázolása.
    
    Args:
        df: LogData DataFrame
        event_index: Az esemény indexe
        event_bg: Az esemény BG értéke
        event_type: 'peak' vagy 'low'
        window_size: Hány időpont előtte és utána (default 30 = ±1.5 óra)
    """
    # Időablak meghatározása
    start_idx = max(0, event_index - window_size)
    end_idx = min(len(df), event_index + window_size + 1)
    
    window_df = df.iloc[start_idx:end_idx].copy()
    
    # Relatív időpont (az esemény = 0 perc)
    relative_times = [(i - event_index) * 3 for i in range(start_idx, end_idx)]  # 3 perces lépések
    
    # Figure setup
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f'Kritikus esemény részletei: {event_type.capitalize()} '
                 f'BG={event_bg:.1f} mg/dL (Időpont: {event_index})', 
                 fontsize=14, fontweight='bold')
    
    # 1. Blood Glucose görbék
    ax1 = axes[0]
    ax1.plot(relative_times, window_df['blood glucose'], 'k-', linewidth=2, label='BG (nyers)')
    
    # WMA vonalak ha vannak a logban
    if 'wma5' in window_df.columns:
        ax1.plot(relative_times, window_df['wma5'], 'orange', linewidth=1.5, alpha=0.8, label='WMA5')
    if 'wma10' in window_df.columns:
        ax1.plot(relative_times, window_df['wma10'], 'blue', linewidth=1.5, alpha=0.7, label='WMA10')
    
    # Kritikus esemény jelölése
    ax1.axvline(x=0, color='red' if event_type == 'peak' else 'blue', 
                linestyle='--', linewidth=2, alpha=0.8, label=f'{event_type.capitalize()} esemény')
    ax1.scatter([0], [event_bg], color='red' if event_type == 'peak' else 'blue', 
                s=100, zorder=5, marker='o')
    
    # Referencia zónák
    ax1.axhspan(70, 130, alpha=0.1, color='green', label='Target zóna')
    ax1.axhspan(130, 180, alpha=0.1, color='yellow')
    ax1.axhspan(180, 400, alpha=0.1, color='red')
    ax1.axhspan(0, 70, alpha=0.1, color='orange')
    
    ax1.set_ylabel('Blood Glucose (mg/dL)')
    ax1.set_title('Vércukorszint alakulása')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(50, min(350, max(window_df['blood glucose']) + 20))
    
    # 2. Étkezések (Meals)
    ax2 = axes[1]
    meal_values = window_df.get('meal', pd.Series([0] * len(window_df), index=window_df.index)).fillna(0)
    
    # Bar plot az étkezésekhez
    meal_bars = ax2.bar(relative_times, meal_values, width=2.5, alpha=0.7, 
                        color='green', label='Étkezés (g CHO)')
    
    # Étkezés értékek megjelenítése a bar-ok tetején (ha > 0)
    for time, meal in zip(relative_times, meal_values):
        if meal > 0:
            ax2.text(time, meal + max(meal_values) * 0.02, f'{meal:.0f}g', 
                    ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    ax2.axvline(x=0, color='red' if event_type == 'peak' else 'blue', 
                linestyle='--', linewidth=2, alpha=0.8)
    
    ax2.set_ylabel('Szénhidrát bevitel (g)')
    ax2.set_title('Étkezések')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    if max(meal_values) > 0:
        ax2.set_ylim(0, max(meal_values) * 1.1)
    
    # 3. Inzulin adagolás (Actions)
    ax3 = axes[2]
    action_values = window_df.get('action', pd.Series([0] * len(window_df), index=window_df.index)).fillna(0)
    
    # Line plot + fill az inzulin adagoláshoz
    ax3.plot(relative_times, action_values, 'purple', linewidth=2, marker='o', 
             markersize=3, label='Inzulin adag')
    ax3.fill_between(relative_times, 0, action_values, alpha=0.3, color='purple')
    
    # Jelentős adagok megjelölése
    for time, action in zip(relative_times, action_values):
        if action > 0.5:  # Csak nagyobb adagokat jelöljük
            ax3.text(time, action + max(action_values) * 0.05, f'{action:.2f}', 
                    ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    ax3.axvline(x=0, color='red' if event_type == 'peak' else 'blue', 
                linestyle='--', linewidth=2, alpha=0.8)
    
    ax3.set_xlabel('Idő (perc a kritikus eseményhez képest)')
    ax3.set_ylabel('Inzulin adag (units)')
    ax3.set_title('Inzulin adagolás')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    if max(action_values) > 0:
        ax3.set_ylim(0, max(action_values) * 1.1)
    
    # X tengely címkézés (időben)
    ax3.set_xlim(relative_times[0], relative_times[-1])
    
    # Időcímkék hozzáadása (óra:perc formátum)
    time_ticks = np.arange(relative_times[0], relative_times[-1] + 1, 30)  # 30 perces lépések
    time_labels = []
    for t in time_ticks:
        hours = int(t // 60)
        minutes = int(t % 60)
        if t < 0:
            time_labels.append(f'{hours}:{minutes:02d}')
        else:
            time_labels.append(f'+{hours}:{minutes:02d}')
    
    ax3.set_xticks(time_ticks)
    ax3.set_xticklabels(time_labels, rotation=45)
    
    plt.tight_layout()
    
    return fig


def visualize_critical_events_detailed(results_dir):
    """
    Kritikus események részletes vizualizációja LogData.csv alapján.
    """
    results_path = Path(results_dir)
    
    # LogData.csv keresése
    log_csv_path = results_path / 'LogData.csv'
    if not log_csv_path.exists():
        print(f'LogData.csv not found in {results_path}')
        return
    
    # Adatok betöltése
    try:
        df = pd.read_csv(log_csv_path)
        print(f'[Critical Timeline] Loaded {len(df)} data points from LogData.csv')
    except Exception as e:
        print(f'Error loading LogData.csv: {e}')
        return
    
    # Kritikus események azonosítása
    critical_events = identify_critical_events_from_log(df)
    
    total_events = len(critical_events['bg_peaks']) + len(critical_events['bg_lows'])
    if total_events == 0:
        print('[Critical Timeline] No critical events found in the data')
        return
    
    print(f'[Critical Timeline] Found {len(critical_events["bg_peaks"])} peaks, '
          f'{len(critical_events["bg_lows"])} lows')
    
    # Csak az összefoglaló plot generálása (részletes timeline-ok eltávolítva)
    create_summary_timeline_plot(df, critical_events, results_path)
    
    print(f'[Critical Timeline] Complete. Generated summary timeline plot only.')
    
    return 1  # Csak 1 plot készül


def create_summary_timeline_plot(df, critical_events, results_path):
    """
    Összefoglaló plot az összes kritikus eseménnyel egy grafikonon.
    """
    fig, ax = plt.subplots(1, 1, figsize=(16, 8))
    
    # Teljes idősor ábrázolása
    time_points = np.arange(len(df)) * 3 / 60  # Órákban
    
    ax.plot(time_points, df['blood glucose'], 'k-', linewidth=1.5, label='Blood Glucose', alpha=0.8)
    
    # Referencia zónák
    ax.axhspan(70, 130, alpha=0.1, color='green', label='Target zóna (70-130)')
    ax.axhspan(130, 180, alpha=0.1, color='yellow', label='Mérsékelt magas (130-180)')
    ax.axhspan(180, 400, alpha=0.1, color='red', label='Hyperglycémia (>180)')
    ax.axhspan(0, 70, alpha=0.1, color='orange', label='Hypoglycémia (<70)')
    
    # Kritikus események jelölése
    for i, (event_idx, bg_value) in enumerate(critical_events['bg_peaks']):
        event_time = event_idx * 3 / 60
        ax.scatter([event_time], [bg_value], color='red', s=80, marker='^', 
                  zorder=5, alpha=0.8)
        ax.annotate(f'P{i+1}\n{bg_value:.0f}', 
                   xy=(event_time, bg_value), 
                   xytext=(5, 10), textcoords='offset points',
                   fontsize=8, ha='left', color='red', fontweight='bold')
    
    for i, (event_idx, bg_value) in enumerate(critical_events['bg_lows']):
        event_time = event_idx * 3 / 60
        ax.scatter([event_time], [bg_value], color='blue', s=80, marker='v', 
                  zorder=5, alpha=0.8)
        ax.annotate(f'L{i+1}\n{bg_value:.0f}', 
                   xy=(event_time, bg_value), 
                   xytext=(5, -15), textcoords='offset points',
                   fontsize=8, ha='left', color='blue', fontweight='bold')
    
    # Étkezések jelölése függőleges vonalakkal
    if 'meal' in df.columns:
        meal_times = df[df['meal'].fillna(0) > 0].index * 3 / 60
        meal_values = df[df['meal'].fillna(0) > 0]['meal']
        
        for meal_time, meal_val in zip(meal_times, meal_values):
            ax.axvline(x=meal_time, color='green', alpha=0.4, linestyle=':', linewidth=2)
            ax.text(meal_time, ax.get_ylim()[1] * 0.95, f'{meal_val:.0f}g', 
                   rotation=90, ha='right', va='top', fontsize=8, color='green')
    
    ax.set_xlabel('Idő (órák)')
    ax.set_ylabel('Blood Glucose (mg/dL)')
    ax.set_title('Kritikus események áttekintése - Teljes szimuláció')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Szebb időtengely
    ax.set_xlim(0, len(df) * 3 / 60)
    
    plt.tight_layout()
    
    summary_path = results_path / 'critical_events_summary_timeline.png'
    fig.savefig(summary_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    print(f'[Critical Timeline] Saved summary timeline: {summary_path}')


def main(results_dir=None):
    """
    Főfunkció - automatikus híváshoz.
    """
    if results_dir is None:
        # Automatikus legfrissebb SimResults könyvtár keresése
        sim_results = Path('SimResults')
        if sim_results.exists():
            subdirs = [p for p in sim_results.iterdir() if p.is_dir()]
            if subdirs:
                results_dir = max(subdirs, key=lambda p: p.stat().st_mtime)
            else:
                print('No SimResults subdirectories found')
                return
        else:
            print('SimResults directory not found')
            return
    
    return visualize_critical_events_detailed(results_dir)


if __name__ == '__main__':
    main()