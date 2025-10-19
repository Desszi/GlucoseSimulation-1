import os
import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
from pathlib import Path

# Lightweight SHAP helper for stable-baselines3 policies
# Usage: run_shap_analysis(model, log_data, out_dir, feature_names=None, n_background=100)

def _build_features_from_log(log_data):
    # simple features: current CGM (blood glucose), recent meal grams (last 60 min), insulin_on_board
    df = pd.DataFrame(log_data)
    if df.empty:
        return np.zeros((0, 3)), ['cgm', 'recent_meal', 'iob']

    # ensure columns
    if 'meal' not in df.columns:
        df['meal'] = 0
    if 'action' not in df.columns:
        df['action'] = 0

    # compute recent_meal for each row: sum meals in previous 60 min (20 steps of 3 min)
    window = 20
    recent_meal = []
    for i in range(len(df)):
        start = max(0, i - window + 1)
        recent_meal.append(df['meal'].iloc[start:i+1].sum())

    # compute simple IOB by linear decay over 4 hours
    iob = []
    decay_hours = 4.0
    for i in range(len(df)):
        t_iob = 0.0
        # iterate past actions
        for j in range(0, i+1):
            elapsed_h = (i - j) * 3.0 / 60.0
            if elapsed_h < decay_hours:
                remaining = max(0.0, 1.0 - elapsed_h / decay_hours)
                t_iob += df['action'].iloc[j] * remaining
        iob.append(t_iob)

    features = np.column_stack([df['blood glucose'].values, np.array(recent_meal), np.array(iob)])
    return features, ['cgm', 'recent_meal', 'iob']


def run_shap_analysis(model, log_data, out_dir: str | Path, model_name: str = 'model', n_background: int = 100):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    features, feature_names = _build_features_from_log(log_data)
    if features.shape[0] == 0:
        print('[SHAP] No log data available for analysis.')
        return

    # sample background
    background = features[np.random.choice(features.shape[0], min(n_background, features.shape[0]), replace=False)]

    # Build a predict function that maps policy action -> actual insulin dose
    # We replicate the same mapping and simple safety caps used in the simulator
    def predict_dose_fn(x):
        # x: (n_samples, n_features) with columns [cgm, recent_meal, iob]
        x = np.asarray(x)
        if x.ndim == 1:
            x = x.reshape(1, -1)

        actions = []
        doses = []
        # constants (keep in sync with simulation_core.apply_insulin_rules)
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

            # call policy with the environment-shaped observation (policy expects CGM-only obs)
            obs_for_policy = np.array([cgm_value])
            act, _ = model.predict(obs_for_policy, deterministic=True)
            try:
                raw = float(np.array(act).ravel()[0])
            except Exception:
                raw = float(act)
            actions.append(raw)

            # dynamic max from recent carbs
            extra_from_carbs = recent_meal / CARB_PER_UNIT
            dynamic_max = min(MAX_CAP, BASE_MAX_DOSE + extra_from_carbs)

            # map raw action to dose
            if -1.0 <= raw <= 1.0:
                dose = max(0.0, (raw + 1.0) / 2.0 * dynamic_max)
            else:
                dose = max(0.0, raw)

            # simple IOB-based predicted drop and cap
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
            # apply simple hypo block
            if cgm_value < TARGET_LOW:
                dose = 0.0

            doses.append(dose)

        # save diagnostics in outer scope after computing full arrays
        predict_dose_fn._last_actions = np.array(actions)
        predict_dose_fn._last_doses = np.array(doses)
        return np.array(doses)

    print('[SHAP] Building KernelExplainer (may be slow for large backgrounds)...')
    explainer = shap.KernelExplainer(predict_dose_fn, background)

    # choose a small subset to explain
    to_explain = features[np.linspace(0, features.shape[0]-1, min(50, features.shape[0])).astype(int)]
    shap_values = explainer.shap_values(to_explain)

    # Diagnostics: actions/doses distribution
    actions = getattr(predict_dose_fn, '_last_actions', None)
    doses = getattr(predict_dose_fn, '_last_doses', None)
    try:
        if actions is None or doses is None:
            # force a call to populate
            _ = predict_dose_fn(to_explain)
            actions = predict_dose_fn._last_actions
            doses = predict_dose_fn._last_doses

        # print summary stats
        print(f"[SHAP] action mean/std/min/max: {actions.mean():.4f}/{actions.std():.4f}/{actions.min():.4f}/{actions.max():.4f}")
        print(f"[SHAP] dose mean/std/min/max: {doses.mean():.4f}/{doses.std():.4f}/{doses.min():.4f}/{doses.max():.4f}")

        # save histograms
        plt.figure()
        plt.hist(actions, bins=30, color='C0', alpha=0.7)
        plt.title(f'Policy action distribution for {model_name}')
        plt.xlabel('action')
        plt.ylabel('count')
        plt.savefig(out_dir / f'actions_hist_{model_name}.png')
        plt.close()

        plt.figure()
        plt.hist(doses, bins=30, color='C1', alpha=0.7)
        plt.title(f'Computed dose distribution for {model_name}')
        plt.xlabel('dose (units)')
        plt.ylabel('count')
        plt.savefig(out_dir / f'doses_hist_{model_name}.png')
        plt.close()

    # scatter action vs dose colored by recent_meal (use to_explain[:,1])
    recent_meals = to_explain[:, 1]
    plt.figure(figsize=(6, 4))
    sc = plt.scatter(actions, doses, c=recent_meals, cmap='viridis', s=18, alpha=0.8)
    plt.colorbar(sc, label='recent_meal (g)')
    plt.title(f'Action vs Dose for {model_name}')
    plt.xlabel('action')
    plt.ylabel('dose (units)')
    plt.grid(True, alpha=0.3)
    plt.savefig(out_dir / f'action_vs_dose_colored_{model_name}.png')
    plt.close()

    # dependence-like plots: dose vs cgm and dose vs recent_meal
    plt.figure(figsize=(6, 3))
    plt.scatter(to_explain[:, 0], doses, c='C2', s=18, alpha=0.8)
    plt.title(f'Dose vs CGM for {model_name}')
    plt.xlabel('CGM (blood glucose)')
    plt.ylabel('dose (units)')
    plt.grid(True, alpha=0.3)
    plt.savefig(out_dir / f'dose_vs_cgm_{model_name}.png')
    plt.close()

    plt.figure(figsize=(6, 3))
    plt.scatter(to_explain[:, 1], doses, c='C3', s=18, alpha=0.8)
    plt.title(f'Dose vs recent_meal for {model_name}')
    plt.xlabel('recent_meal (g)')
    plt.ylabel('dose (units)')
    plt.grid(True, alpha=0.3)
    plt.savefig(out_dir / f'dose_vs_recentmeal_{model_name}.png')
    plt.close()
    print(f'[SHAP] Saved diagnostics to {out_dir}')
    except Exception as e:
        print('[SHAP] diagnostics generation failed:', e)

    # summary plot
    plt.figure()
    shap.summary_plot(shap_values, to_explain, feature_names=feature_names, show=False)
    plt.title(f'SHAP summary for {model_name}')
    plt.savefig(out_dir / f'shap_summary_{model_name}.png')
    plt.close()
    print(f'[SHAP] Saved summary plot to {out_dir / f"shap_summary_{model_name}.png"}')

    # force plot for first sample
    try:
        # create a matplotlib force plot and save as PNG (more portable than HTML here)
        plt.figure(figsize=(6, 3))
        shap.force_plot(explainer.expected_value, shap_values[0], to_explain[0], feature_names=feature_names, matplotlib=True, show=False)
        plt.title(f'SHAP force plot for {model_name} (first sample)')
        plt.tight_layout()
        png_path = out_dir / f'shap_force_{model_name}.png'
        plt.savefig(png_path, dpi=150)
        plt.close()
        print(f'[SHAP] Saved force plot (png) to {png_path}')
    except Exception as e:
        print('[SHAP] force_plot failed:', e)

    return True
