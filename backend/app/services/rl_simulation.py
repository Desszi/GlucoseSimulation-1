from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import json
import pandas as pd
def _lazy_imports():
    from simulation_core import (
        SimulationConfig, MealGenerator, EnvironmentManager,
        ModelTrainer, SimulationRunner, MetricsCalculator, DataSaver
    )
    from simglucose.simulation.scenario import CustomScenario
    return SimulationConfig, MealGenerator, EnvironmentManager, ModelTrainer, SimulationRunner, MetricsCalculator, DataSaver, CustomScenario

# NOTE: We intentionally keep training timesteps fixed (5000) as in desktop main.py.
# API always produces a fresh 24h run (3 min step -> 480 steps) regardless of user input; meals come from UI.


def build_custom_scenario_from_ui(meals: List[Dict[str, Any]]):
    # Use lazy import for CustomScenario
    _, _, _, _, _, _, _, CustomScenario = _lazy_imports()
    """UI meal list -> CustomScenario.
    Expects each meal dict: {timestamp: 'HH:MM' or ISO, carbs_g: int}
    We map start_time to fixed midnight reference and convert absolute minutes to hour float pairs.
    The runner in simulation_core expects scenario format: list of (time_hour_float, CHO grams).
    We approximate meal absorption start at provided timestamp; duration not required by CustomScenario (env handles it).
    """
    if not meals:
        return CustomScenario(start_time=datetime(2025,1,1), scenario=[])
    # Normalise to date 2025-01-01
    scenario_items = []
    base_day = datetime(2025,1,1)
    for m in meals:
        ts = m.get('timestamp')
        carbs = int(m.get('carbs_g', 0))
        if not ts:
            continue
        # Accept HH:MM or full ISO
        if 'T' in ts:
            dt = datetime.fromisoformat(ts)
        else:
            hour, minute = ts.split(':')[0:2]
            dt = base_day.replace(hour=int(hour), minute=int(minute))
        minutes = (dt - base_day).total_seconds()/60.0
        hour_float = minutes/60.0
        scenario_items.append((hour_float, carbs))
    scenario_items.sort(key=lambda x: x[0])
    return CustomScenario(start_time=base_day, scenario=scenario_items)


def run_rl_full_day(meals: List[Dict[str, Any]], force_train: bool = False) -> Dict[str, Any]:
    """Train (unless models exist and force_train False) and run 24h RL simulation with custom meals.
    Model type is forced to PPO to mirror desktop main.py behavior.
    Returns JSON-friendly dict containing log, metrics, model summary.
    """
    # Config & patient params (forced PPO)
    SimulationConfig, MealGenerator, EnvironmentManager, ModelTrainer, SimulationRunner, MetricsCalculator, DataSaver, CustomScenario = _lazy_imports()
    model_type = "PPO"
    config = SimulationConfig(model_type=model_type)
    patient_params = config.get_patient_params()

    # Replace generated meals with UI meals
    scenario = build_custom_scenario_from_ui(meals)

    # Environment management (path for outputs)
    env_mgr = EnvironmentManager(config, scenario)
    env_mgr.register_environments()
    env, lowenv, innerenv, highenv = env_mgr.create_environments()

    # Train or load
    trainer = ModelTrainer(lowenv, innerenv, highenv, config)
    lowmodel, innermodel, highmodel = trainer.train_or_load_models(use_existing_models=not force_train)

    # Run
    runner = SimulationRunner(env, lowmodel, innermodel, highmodel, config)
    frames, log_data = runner.run()

    # Metrics
    metrics_calc = MetricsCalculator(env_mgr.path_to_results)
    metrics = metrics_calc.calculate(log_data)

    # Extra summary stats
    df = pd.DataFrame(log_data)
    metrics.update({
        'Avg_BG': float(df['blood glucose'].mean()),
        'Max_BG': float(df['blood glucose'].max()),
        'Min_BG': float(df['blood glucose'].min()),
        'StdDev_BG': float(df['blood glucose'].std()),
        'Total_Doses': float(df['dose'].sum()),
        'Meals_Count': int((df['meal']>0).sum()),
        'ModelType': model_type,
        'TimeSteps': config.time_steps,
        'Duration_hours': 24
    })

    # Persist CSV (video optional off by default)
    try:
        saver = DataSaver(env_mgr.path_to_results, config)
        saver.save_csv(log_data)
    except Exception:
        pass

    # Prepare minimal series for frontend (compress)
    series = [
        {
            'time': row['time'],
            'bg': row['blood glucose'],
            'dose': row['dose'],
            'meal': row['meal']
        } for row in log_data
    ]

    # Model selection summary if created
    model_summary_path = env_mgr.path_to_results / 'model_selection_summary.json'
    model_summary = {}
    if model_summary_path.exists():
        try:
            model_summary = json.loads(model_summary_path.read_text())
        except Exception:
            pass

    env.close()
    # --- Sanitize numpy types ---
    def _py(v):
        import numpy as np
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.ndarray,)):
            return v.tolist()
        return v
    series_py = [{k: _py(v) for k, v in p.items()} for p in series]
    metrics_py = {k: _py(v) for k, v in metrics.items()}
    model_summary_py = {k: {ik: _py(iv) for ik, iv in inner.items()} for k, inner in model_summary.items()} if isinstance(model_summary, dict) else model_summary

    return {
        'series': series_py,
        'metrics': metrics_py,
        'model_summary': model_summary_py,
        'results_path': str(env_mgr.path_to_results)
    }
