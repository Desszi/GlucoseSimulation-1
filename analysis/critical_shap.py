import os
import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
from pathlib import Path

def identify_critical_events(log_data):
    """
    Kritikus CGM események azonosítása: lokális maximumok és minimumok.
    
    Returns:
        dict: {'bg_peaks': indices, 'bg_lows': indices}
    """
    df = pd.DataFrame(log_data)
    if df.empty or 'blood glucose' not in df.columns:
        return {}
    
    bg_values = df['blood glucose'].values
    critical_events = {}
    
    # Lokális maximumok keresése (tetőpontok)
    # Egy pont maximum, ha nagyobb mint mindkét szomszédja és > 160 mg/dL
    peak_indices = []
    for i in range(1, len(bg_values) - 1):
        if (bg_values[i] > bg_values[i-1] and 
            bg_values[i] > bg_values[i+1] and 
            bg_values[i] > 160):  # Csak magas értékeknél
            peak_indices.append(i)
    
    # Lokális minimumok keresése (mélypontok) 
    # Egy pont minimum, ha kisebb mint mindkét szomszédja és < 100 mg/dL
    low_indices = []
    for i in range(1, len(bg_values) - 1):
        if (bg_values[i] < bg_values[i-1] and 
            bg_values[i] < bg_values[i+1] and 
            bg_values[i] < 100):  # Csak alacsony értékeknél
            low_indices.append(i)
    
    # Top 5 legmagasabb csúcs
    if peak_indices:
        peak_values = [(i, bg_values[i]) for i in peak_indices]
        peak_values.sort(key=lambda x: x[1], reverse=True)  # BG érték szerint csökkenő
        top_peaks = [x[0] for x in peak_values[:5]]
        critical_events['bg_peaks'] = top_peaks
    else:
        critical_events['bg_peaks'] = []
    
    # Top 5 legalacsonyabb mélypont
    if low_indices:
        low_values = [(i, bg_values[i]) for i in low_indices]
        low_values.sort(key=lambda x: x[1])  # BG érték szerint növekvő
        top_lows = [x[0] for x in low_values[:5]]
        critical_events['bg_lows'] = top_lows
    else:
        critical_events['bg_lows'] = []
    
    return critical_events


def _build_features_from_log(log_data):
    """Kibővített feature építés a prediktív jellemzőkkel."""
    df = pd.DataFrame(log_data)
    if df.empty:
        return np.zeros((0, 6)), ['cgm', 'recent_meal', 'iob', 'slope', 'wma5', 'predicted_peak']

    # Alapértelmezett oszlopok biztosítása
    for col in ['meal', 'action', 'slope', 'wma5', 'predicted_peak']:
        if col not in df.columns:
            df[col] = 0

    # Recent meal számítása (utolsó 60 perc = 20 lépés)
    window = 20
    recent_meal = []
    for i in range(len(df)):
        start = max(0, i - window + 1)
        recent_meal.append(df['meal'].iloc[start:i+1].sum())

    # IOB számítása lineáris decay-jel (4 óra)
    iob = []
    decay_hours = 4.0
    for i in range(len(df)):
        t_iob = 0.0
        for j in range(0, i+1):
            elapsed_h = (i - j) * 3.0 / 60.0
            if elapsed_h < decay_hours:
                remaining = max(0.0, 1.0 - elapsed_h / decay_hours)
                t_iob += df['action'].iloc[j] * remaining
        iob.append(t_iob)

    # Feature mátrix összeállítása
    features = np.column_stack([
        df['blood glucose'].values,
        np.array(recent_meal),
        np.array(iob),
        df['slope'].values,
        df['wma5'].values,
        df['predicted_peak'].values
    ])
    
    feature_names = ['cgm', 'recent_meal', 'iob', 'slope', 'wma5', 'predicted_peak']
    return features, feature_names


def analyze_critical_shap(model, log_data, out_dir: str | Path, model_name: str = 'model', n_background: int = 100):
    """
    Kritikus CGM események lokális SHAP analízise és vizualizációja.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f'[Critical SHAP] Starting analysis for {model_name}...')
    
    # Kritikus események azonosítása
    critical_events = identify_critical_events(log_data)
    if not critical_events:
        print('[Critical SHAP] No critical events found.')
        return
    
    # Feature építés
    features, feature_names = _build_features_from_log(log_data)
    if features.shape[0] == 0:
        print('[Critical SHAP] No features available.')
        return
    
    # Background minta
    background = features[np.random.choice(features.shape[0], min(n_background, features.shape[0]), replace=False)]
    
    # Predict függvény (ugyanaz mint az eredeti shap_helper-ben)
    def predict_dose_fn(x):
        x = np.asarray(x)
        if x.ndim == 1:
            x = x.reshape(1, -1)

        doses = []
        BASE_MAX_DOSE = 3.5
        MAX_CAP = 10.0
        TARGET_LOW = 70.0
        SAFETY_MARGIN = 10.0
        CARB_PER_UNIT = 10.0
        ISF = 40.0

        for row in x:
            cgm_value = float(row[0])
            recent_meal = float(row[1])
            iob_feature = float(row[2])

            obs_for_policy = np.array([cgm_value])
            act, _ = model.predict(obs_for_policy, deterministic=True)
            try:
                raw = float(np.array(act).ravel()[0])
            except Exception:
                raw = float(act)

            extra_from_carbs = recent_meal / CARB_PER_UNIT
            dynamic_max = min(MAX_CAP, BASE_MAX_DOSE + extra_from_carbs)

            if -1.0 <= raw <= 1.0:
                dose = max(0.0, (raw + 1.0) / 2.0 * dynamic_max)
            else:
                dose = max(0.0, raw)

            predicted_drop_from_iob = iob_feature * ISF
            allowable_drop = cgm_value - TARGET_LOW - SAFETY_MARGIN
            if allowable_drop < 0:
                allowable_drop = 0.0

            predicted_drop_with_new = predicted_drop_from_iob + dose * ISF
            if predicted_drop_with_new > allowable_drop:
                max_additional_units = max(0.0, (allowable_drop - predicted_drop_from_iob) / ISF)
                dose = min(dose, max_additional_units)
                if dose < 1e-3:
                    dose = 0.0

            dose = min(dose, dynamic_max)
            if cgm_value < TARGET_LOW:
                dose = 0.0

            doses.append(dose)

        return np.array(doses)
    
    # SHAP explainer
    print('[Critical SHAP] Building explainer...')
    explainer = shap.KernelExplainer(predict_dose_fn, background)
    
    # Kritikus események típusonkénti elemzése
    event_colors = {
        'bg_peaks': 'red',
        'bg_lows': 'blue'
    }
    
    event_labels = {
        'bg_peaks': 'Vércukor tetőpontok (lokális max >160)',
        'bg_lows': 'Vércukor mélypontok (lokális min <100)'
    }
    
    # Összesített kritikus események plot (csak 2 subplot: peaks és lows)
    plt.figure(figsize=(12, 5))
    
    for event_type, indices in critical_events.items():
        if not indices:
            continue
            
        print(f'[Critical SHAP] Analyzing {event_type}: {len(indices)} events')
        
        # Maximum 10 esemény típusonként (teljesítmény miatt)
        sample_indices = indices[:10] if len(indices) > 10 else indices
        critical_features = features[sample_indices]
        
        # SHAP értékek számítása
        shap_values = explainer.shap_values(critical_features)
        
        # Átlagos SHAP értékek típusonként
        mean_shap = np.mean(np.abs(shap_values), axis=0)
        
        # Subplot az aktuális event típushoz
        subplot_idx = 1 if event_type == 'bg_peaks' else 2
        plt.subplot(1, 2, subplot_idx)
        bars = plt.bar(feature_names, mean_shap, color=event_colors[event_type], alpha=0.7)
        plt.title(f'{event_labels[event_type]}\n(Átlagos |SHAP| értékek)')
        plt.ylabel('Átlagos |SHAP| érték')
        plt.xticks(rotation=45)
        
        # Értékek megjelenítése a bar-ok tetején
        for bar, val in zip(bars, mean_shap):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                    f'{val:.3f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(out_dir / f'critical_shap_summary_{model_name}.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # Force plot-ok eltávolítva (túl sok diagram)
    
    # Heatmap: feature importance kritikus események szerint (csak peaks vs lows)
    plt.figure(figsize=(8, 4))
    importance_matrix = []
    event_names = []
    
    for event_type, indices in critical_events.items():
        if not indices:
            continue
            
        sample_indices = indices[:5]  # Maximum 5 esemény típusonként
        critical_features = features[sample_indices]
        shap_values = explainer.shap_values(critical_features)
        
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        importance_matrix.append(mean_abs_shap)
        event_names.append(event_labels[event_type])
    
    if importance_matrix:
        importance_matrix = np.array(importance_matrix)
        
        im = plt.imshow(importance_matrix, cmap='RdYlBu_r', aspect='auto')
        plt.colorbar(im, label='Átlagos |SHAP| érték')
        
        plt.xticks(range(len(feature_names)), feature_names, rotation=45)
        plt.yticks(range(len(event_names)), event_names)
        plt.title(f'Feature fontosság: Tetőpontok vs. Mélypontok - {model_name}')
        
        # Értékek megjelenítése a cellákban
        for i in range(len(event_names)):
            for j in range(len(feature_names)):
                color = 'white' if importance_matrix[i, j] > np.max(importance_matrix) * 0.5 else 'black'
                plt.text(j, i, f'{importance_matrix[i, j]:.3f}',
                        ha='center', va='center', fontsize=10, color=color, weight='bold')
        
        plt.tight_layout()
        plt.savefig(out_dir / f'critical_heatmap_{model_name}.png', dpi=150, bbox_inches='tight')
        plt.close()
    
    # Statisztikák kiírása
    stats_path = out_dir / f'critical_events_stats_{model_name}.txt'
    with open(stats_path, 'w') as f:
        f.write(f'Kritikus események statisztikái - {model_name}\n')
        f.write('=' * 50 + '\n\n')
        
        for event_type, indices in critical_events.items():
            f.write(f'{event_labels[event_type]}: {len(indices)} esemény\n')
            if indices:
                bg_values = [log_data[i]['blood glucose'] for i in indices]
                f.write(f'  BG tartomány: {min(bg_values):.1f} - {max(bg_values):.1f} mg/dL\n')
                f.write(f'  BG átlag: {np.mean(bg_values):.1f} mg/dL\n')
                f.write(f'  Időpontok: {indices[:10]}...\n')  # Első 10 index
            f.write('\n')
    
    print(f'[Critical SHAP] Analysis complete. Results saved to {out_dir}')
    print(f'[Critical SHAP] Statistics saved to {stats_path}')
    
    return True