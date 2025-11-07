import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

"""
Egyszerű vizualizáció a raw BG, WMA5, WMA10 és blended peak előrejelzéshez.
Futtatás előtt győződj meg róla, hogy létezik a LogData.csv (Simulation után). 
"""

def weighted_moving_average(series, window):
    if len(series) < window:
        return np.array(series)
    out = []
    weights = np.arange(1, window + 1, dtype=float)
    wsum = weights.sum()
    for i in range(len(series)):
        if i + 1 < window:
            out.append(series[i])
        else:
            segment = series[i - window + 1: i + 1]
            out.append(np.dot(segment, weights) / wsum)
    return np.array(out)


def main(log_csv_path: Path):
    df = pd.read_csv(log_csv_path)
    if 'blood glucose' not in df.columns:
        raise ValueError("A CSV nem tartalmaz 'blood glucose' oszlopot.")

    bg = df['blood glucose'].astype(float).values
    wma5 = weighted_moving_average(bg, 5)
    wma10 = weighted_moving_average(bg, 10)

    # Egyszerű slope WMA5
    slope_wma5 = np.diff(wma5, prepend=wma5[0])
    horizon_steps = 12
    pred_peak_raw = bg + np.maximum(0, np.diff(bg, prepend=bg[0])) * horizon_steps
    pred_peak_wma = wma5 + np.maximum(0, slope_wma5) * horizon_steps
    blended = 0.5 * pred_peak_raw + 0.5 * pred_peak_wma

    plt.figure(figsize=(12, 6))
    plt.plot(bg, label='Raw BG', color='black', linewidth=1)
    plt.plot(wma5, label='WMA5', color='orange')
    plt.plot(wma10, label='WMA10', color='blue', alpha=0.7)
    plt.plot(blended, label='Blended Pred Peak', color='red', linestyle='--')

    # Étkezések jelölése (ha 'meal' oszlop van és >0)
    if 'meal' in df.columns:
        meal_idx = np.where(df['meal'].fillna(0).astype(float).values > 0)[0]
        plt.scatter(meal_idx, bg[meal_idx], marker='o', color='green', s=30, label='Meal')

    plt.title('BG vs Weighted Moving Averages and Predicted Peak')
    plt.xlabel('Time step')
    plt.ylabel('BG (mg/dL)')
    plt.legend()
    plt.grid(alpha=0.3)
    out_path = log_csv_path.parent / 'wma_plot.png'
    plt.tight_layout()
    plt.savefig(out_path)
    print(f"Mentve: {out_path}")


if __name__ == '__main__':
    # Alapértelmezett path a legutóbbi futáshoz (SimResults alatti legfrissebb könyvtárat megkereshetnénk
    # de itt explicit path-ot várunk vagy a default-ot próbáljuk)
    default = Path('SimResults')
    # Egyszerű stratégia: legutóbb módosított mappa keresése
    if default.exists():
        subdirs = [p for p in default.iterdir() if p.is_dir()]
        if not subdirs:
            print('Nincs SimResults almappa.')
        else:
            latest = max(subdirs, key=lambda p: p.stat().st_mtime)
            log_csv = latest / 'LogData.csv'
            if log_csv.exists():
                main(log_csv)
            else:
                print(f'Nem található LogData.csv ebben: {latest}')
    else:
        print('SimResults könyvtár nem létezik.')
