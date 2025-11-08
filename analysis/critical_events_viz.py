import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import re

"""
Critical events statistics vizualizáció.
Beolvassa a critical_events_stats_*.txt fájlokat és matplotlib chartokat készít.
"""

def parse_stats_file(file_path):
    """
    Egy critical_events_stats_*.txt fájl parse-olása.
    
    Returns:
        dict: {
            'model_name': str,
            'bg_peaks': {'count': int, 'bg_range': (min, max), 'bg_avg': float},
            'bg_lows': {'count': int, 'bg_range': (min, max), 'bg_avg': float}
        }
    """
    data = {'model_name': '', 'bg_peaks': {}, 'bg_lows': {}}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Model név kinyerése a fájlnév alapján
        model_match = re.search(r'critical_events_stats_(\w+)\.txt', file_path.name)
        if model_match:
            data['model_name'] = model_match.group(1)
        
        # Tetőpontok parse-olása
        peaks_pattern = r'Vércukor tetőpontok.*?(\d+) esemény\s*BG tartomány: ([\d.]+) - ([\d.]+) mg/dL\s*BG átlag: ([\d.]+) mg/dL'
        peaks_match = re.search(peaks_pattern, content, re.DOTALL)
        if peaks_match:
            count = int(peaks_match.group(1))
            min_bg = float(peaks_match.group(2))
            max_bg = float(peaks_match.group(3))
            avg_bg = float(peaks_match.group(4))
            data['bg_peaks'] = {
                'count': count,
                'bg_range': (min_bg, max_bg),
                'bg_avg': avg_bg
            }
        else:
            data['bg_peaks'] = {'count': 0, 'bg_range': (0, 0), 'bg_avg': 0}
        
        # Mélypontok parse-olása
        lows_pattern = r'Vércukor mélypontok.*?(\d+) esemény\s*BG tartomány: ([\d.]+) - ([\d.]+) mg/dL\s*BG átlag: ([\d.]+) mg/dL'
        lows_match = re.search(lows_pattern, content, re.DOTALL)
        if lows_match:
            count = int(lows_match.group(1))
            min_bg = float(lows_match.group(2))
            max_bg = float(lows_match.group(3))
            avg_bg = float(lows_match.group(4))
            data['bg_lows'] = {
                'count': count,
                'bg_range': (min_bg, max_bg),
                'bg_avg': avg_bg
            }
        else:
            data['bg_lows'] = {'count': 0, 'bg_range': (0, 0), 'bg_avg': 0}
            
    except Exception as e:
        print(f'Error parsing {file_path}: {e}')
        
    return data


def visualize_critical_events_stats(results_dir):
    """
    Critical events statisztikák vizualizációja a results könyvtárból.
    
    Args:
        results_dir: Path to the SimResults directory containing stats files
    """
    results_path = Path(results_dir)
    
    # Stats fájlok keresése
    stats_files = list(results_path.glob('critical_events_stats_*.txt'))
    
    if not stats_files:
        print(f'No critical_events_stats_*.txt files found in {results_path}')
        return
    
    # Adatok parse-olása
    all_data = []
    for file_path in stats_files:
        data = parse_stats_file(file_path)
        if data['model_name']:
            all_data.append(data)
    
    if not all_data:
        print('No valid stats data found')
        return
    
    # Modellek rendezése
    model_order = ['lowmodel', 'innermodel', 'highmodel']
    all_data.sort(key=lambda x: model_order.index(x['model_name']) if x['model_name'] in model_order else 99)
    
    model_names = [d['model_name'] for d in all_data]
    
    # 1. Események száma (bar chart)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Critical Events Statistics Összehasonlítás', fontsize=16, fontweight='bold')
    
    # 1a. Események száma
    ax1 = axes[0, 0]
    peaks_counts = [d['bg_peaks']['count'] for d in all_data]
    lows_counts = [d['bg_lows']['count'] for d in all_data]
    
    x = np.arange(len(model_names))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, peaks_counts, width, label='Tetőpontok', color='red', alpha=0.7)
    bars2 = ax1.bar(x + width/2, lows_counts, width, label='Mélypontok', color='blue', alpha=0.7)
    
    ax1.set_xlabel('Modellek')
    ax1.set_ylabel('Események száma')
    ax1.set_title('Kritikus események száma modellenkint')
    ax1.set_xticks(x)
    ax1.set_xticklabels(model_names)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Értékek megjelenítése a bar-ok tetején
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{int(height)}', ha='center', va='bottom')
    for bar in bars2:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{int(height)}', ha='center', va='bottom')
    
    # 1b. Átlagos BG értékek tetőpontokban és mélypontokban
    ax2 = axes[0, 1]
    peaks_avg = [d['bg_peaks']['bg_avg'] for d in all_data]
    lows_avg = [d['bg_lows']['bg_avg'] for d in all_data]
    
    bars3 = ax2.bar(x - width/2, peaks_avg, width, label='Tetőpontok átlag', color='red', alpha=0.7)
    bars4 = ax2.bar(x + width/2, lows_avg, width, label='Mélypontok átlag', color='blue', alpha=0.7)
    
    ax2.set_xlabel('Modellek')
    ax2.set_ylabel('Átlagos BG (mg/dL)')
    ax2.set_title('Átlagos BG értékek kritikus eseményeknél')
    ax2.set_xticks(x)
    ax2.set_xticklabels(model_names)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Target zónák jelölése
    ax2.axhline(y=70, color='orange', linestyle='--', alpha=0.5, label='Hypo határ')
    ax2.axhline(y=130, color='green', linestyle='--', alpha=0.5, label='Target felső határ')
    ax2.axhline(y=180, color='red', linestyle='--', alpha=0.5, label='Hyper határ')
    
    # Értékek megjelenítése
    for bar, val in zip(bars3, peaks_avg):
        if val > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 5,
                    f'{val:.1f}', ha='center', va='bottom', fontweight='bold')
    for bar, val in zip(bars4, lows_avg):
        if val > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                    f'{val:.1f}', ha='center', va='bottom', fontweight='bold')
    
    # 2. BG tartományok (min-max) box plot stílusban
    ax3 = axes[1, 0]
    
    # Tetőpontok tartományai
    for i, data in enumerate(all_data):
        if data['bg_peaks']['count'] > 0:
            min_val, max_val = data['bg_peaks']['bg_range']
            avg_val = data['bg_peaks']['bg_avg']
            
            # Tartomány vonal
            ax3.plot([i-0.1, i-0.1], [min_val, max_val], 'r-', linewidth=3, alpha=0.7)
            # Min-max pontok
            ax3.plot(i-0.1, min_val, 'rv', markersize=8, alpha=0.8)
            ax3.plot(i-0.1, max_val, 'r^', markersize=8, alpha=0.8)
            # Átlag pont
            ax3.plot(i-0.1, avg_val, 'ro', markersize=6, alpha=0.9)
    
    # Mélypontok tartományai
    for i, data in enumerate(all_data):
        if data['bg_lows']['count'] > 0:
            min_val, max_val = data['bg_lows']['bg_range']
            avg_val = data['bg_lows']['bg_avg']
            
            # Tartomány vonal
            ax3.plot([i+0.1, i+0.1], [min_val, max_val], 'b-', linewidth=3, alpha=0.7)
            # Min-max pontok
            ax3.plot(i+0.1, min_val, 'bv', markersize=8, alpha=0.8)
            ax3.plot(i+0.1, max_val, 'b^', markersize=8, alpha=0.8)
            # Átlag pont
            ax3.plot(i+0.1, avg_val, 'bo', markersize=6, alpha=0.9)
    
    ax3.set_xlabel('Modellek')
    ax3.set_ylabel('BG tartomány (mg/dL)')
    ax3.set_title('BG értékek tartományai (min-átlag-max)')
    ax3.set_xticks(range(len(model_names)))
    ax3.set_xticklabels(model_names)
    ax3.grid(True, alpha=0.3)
    
    # Referencia vonalak
    ax3.axhline(y=70, color='orange', linestyle='--', alpha=0.5)
    ax3.axhline(y=130, color='green', linestyle='--', alpha=0.5)
    ax3.axhline(y=180, color='red', linestyle='--', alpha=0.5)
    
    # Legenda
    import matplotlib.lines as mlines
    red_line = mlines.Line2D([], [], color='red', marker='o', linestyle='-', 
                            markersize=8, label='Tetőpontok (min-átlag-max)')
    blue_line = mlines.Line2D([], [], color='blue', marker='o', linestyle='-',
                             markersize=8, label='Mélypontok (min-átlag-max)')
    ax3.legend(handles=[red_line, blue_line])
    
    # 3. Összefoglaló táblázat szöveges formában
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Táblázat adatok
    table_data = []
    headers = ['Model', 'Peaks\n(count)', 'Peak Avg\n(mg/dL)', 'Lows\n(count)', 'Low Avg\n(mg/dL)']
    
    for data in all_data:
        row = [
            data['model_name'],
            str(data['bg_peaks']['count']),
            f"{data['bg_peaks']['bg_avg']:.1f}" if data['bg_peaks']['count'] > 0 else "N/A",
            str(data['bg_lows']['count']),
            f"{data['bg_lows']['bg_avg']:.1f}" if data['bg_lows']['count'] > 0 else "N/A"
        ]
        table_data.append(row)
    
    # Matplotlib táblázat
    table = ax4.table(cellText=table_data, colLabels=headers,
                     cellLoc='center', loc='center',
                     colWidths=[0.2, 0.15, 0.2, 0.15, 0.2])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Fejléc formázás
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Sorok színezése
    for i in range(1, len(table_data) + 1):
        for j in range(len(headers)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
    
    ax4.set_title('Összefoglaló táblázat', fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # Mentés
    output_path = results_path / 'critical_events_visualization.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'[Critical Events Viz] Saved visualization to {output_path}')
    
    return output_path


def main(results_dir=None):
    """
    Főfunkció - automatikus híváshoz.
    
    Args:
        results_dir: Optional path to results directory. 
                    If None, looks for latest in SimResults/
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
    
    return visualize_critical_events_stats(results_dir)


if __name__ == '__main__':
    main()