import os
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # fej nélküli render
import matplotlib.pyplot as plt
import numpy as np

try:
    from simglucose.simulation.scenario import CustomScenario
    import gymnasium
    _SIMGLUCOSE_AVAILABLE = True
except Exception as e:  # ImportError vagy namespace hiba
    _SIMGLUCOSE_AVAILABLE = False
    _SIMGLUCOSE_IMPORT_ERR = e


def _meals_to_scenario(meals: List[Dict]) -> CustomScenario:
    """Alakítsa át a DB meal rekordokat a simglucose CustomScenario formátumára.
    Input meal dict: {id, timestamp (ISO), carbs_g, meal_type, notes}
    A scenario lista: [(hour_float, grams), ...]. hour_float a nap elejétől eltelt órák.
    """
    if not meals:
        return CustomScenario(start_time=datetime(2025, 1, 1), scenario=[])
    # Alap kezdőnap: a legkorábbi étkezés napja 00:00-ra igazítva
    raw_first = meals[0].timestamp
    if 'T' not in raw_first and len(raw_first) in (5,8):  # HH:MM or HH:MM:SS
        today = datetime.utcnow().date().strftime('%Y-%m-%d')
        if len(raw_first) == 5:  # HH:MM
            raw_first = f"{today}T{raw_first}:00"
        else:  # HH:MM:SS
            raw_first = f"{today}T{raw_first}"
    first_dt = datetime.fromisoformat(raw_first)
    start_of_day = first_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    scenario_items: List[Tuple[float, int]] = []
    for m in meals:
        ts = m.timestamp
        if 'T' not in ts and len(ts) in (5,8):
            today = first_dt.date().strftime('%Y-%m-%d')
            if len(ts) == 5:
                ts = f"{today}T{ts}:00"
            else:
                ts = f"{today}T{ts}"
        dt = datetime.fromisoformat(ts)
        delta_min = (dt - start_of_day).total_seconds() / 60.0
        hour_float = delta_min / 60.0
        scenario_items.append((hour_float, int(m.carbs_g)))
    # idő szerint rendezés
    scenario_items.sort(key=lambda x: x[0])
    return CustomScenario(start_time=start_of_day, scenario=scenario_items)


def run_simple_simulation(patient_name: str, meals: List, timesteps: int = 500) -> Dict:
    """Egyszerű szimuláció RL modellek nélkül (dózis=0 végig).
    Visszaad: {
       'log': [{'t': step, 'bg': value, 'meal': grams}],
       'metrics': {...},
       'start_time': iso,
       'end_time': iso
    }
    """
    scenario = _meals_to_scenario(meals)
    # Környezet létrehozása custom scenario-val
    if not _SIMGLUCOSE_AVAILABLE:
        # Fallback: mesterséges szinusz BG + meal ingest jelölés
        log = []
        meal_list = list(scenario.scenario)
        meal_triggered = set()
        import math
        for step in range(timesteps):
            current_hour = step * 5 / 60.0
            meal_grams = 0
            for mh, grams in meal_list:
                if mh <= current_hour and (mh, grams) not in meal_triggered:
                    meal_grams += grams
                    meal_triggered.add((mh, grams))
            bg = 110 + 25 * math.sin(step/30.0) + (meal_grams * 0.5)
            log.append({'t': step, 'bg': bg, 'meal': meal_grams, 'reward': 0.0})
        bgs = [row['bg'] for row in log]
        tir = sum(1 for v in bgs if 70 <= v <= 130) / max(1, len(bgs)) * 100.0
        hypo = sum(1 for v in bgs if v < 70)
        hyper = sum(1 for v in bgs if v > 180)
        avg_bg = sum(bgs) / max(1, len(bgs))
        metrics = {
            'TIR_percent': tir,
            'Hypo_events': hypo,
            'Hyper_events': hyper,
            'Avg_BG': avg_bg,
            'Samples': len(bgs),
            'mode': 'simple-fallback',
            'fallback': True,
            'reason': 'simglucose gym namespace unavailable'
        }
        return {
            'log': log,
            'metrics': metrics,
            'start_time': scenario.start_time.isoformat(),
            'end_time': scenario.start_time.isoformat()
        }

    try:
        env = gymnasium.make("simglucose/adolescent2-v0", render_mode=None, patient_name=patient_name, custom_scenario=scenario)
        obs, info = env.reset()
    except Exception as e:
        # Próbáljuk meg közvetlen T1DSimEnv példányosítást ha elérhető
        try:
            try:
                from simglucose.patient.t1dpatient import T1DPatient
                from simglucose.sensor.cgm import CGMSensor
                from simglucose.simulation.env import T1DSimEnv
            except Exception:
                # Ha bármelyik import bukik, ugrunk fallback-ra
                raise
            # Scenario adapter: scenario.scenario [(hour, grams)] -> a T1DSimEnv scenario objektum kompatibilis CustomScenario
            patient = T1DPatient.withName(patient_name) if hasattr(T1DPatient, 'withName') else T1DPatient(patient_name)
            sensor = CGMSensor.withName('Dexcom', seed=0)
            # Pump komponens nem elérhető a jelen környezetben, helyettesítjük None-nal ha konstruktor megengedi
            pump = None
            env = T1DSimEnv(patient, sensor, pump, scenario) if 'T1DSimEnv' in globals() else None
            if env is None:
                raise RuntimeError('T1DSimEnv unavailable')
            obs = env.reset()
        except Exception:
            # Ha ez is elhasal, térjünk vissza a korábbi synthetic fallback logikára
            import math
            log = []
            meal_list = list(scenario.scenario)
            meal_triggered = set()
            for step in range(timesteps):
                current_hour = step * 5 / 60.0
                meal_grams = 0
                for mh, grams in meal_list:
                    if mh <= current_hour and (mh, grams) not in meal_triggered:
                        meal_grams += grams
                        meal_triggered.add((mh, grams))
                bg = 110 + 25 * math.sin(step/30.0) + (meal_grams * 0.5)
                log.append({'t': step, 'bg': bg, 'meal': meal_grams, 'reward': 0.0})
            bgs = [row['bg'] for row in log]
            tir = sum(1 for v in bgs if 70 <= v <= 130) / max(1, len(bgs)) * 100.0
            hypo = sum(1 for v in bgs if v < 70)
            hyper = sum(1 for v in bgs if v > 180)
            avg_bg = sum(bgs) / max(1, len(bgs))
            metrics = {
                'TIR_percent': tir,
                'Hypo_events': hypo,
                'Hyper_events': hyper,
                'Avg_BG': avg_bg,
                'Samples': len(bgs),
                'mode': 'simple-fallback',
                'fallback': True,
                'reason': 'env creation failed'
            }
            return {
                'log': log,
                'metrics': metrics,
                'start_time': scenario.start_time.isoformat(),
                'end_time': scenario.start_time.isoformat()
            }
        import math
        log = []
        meal_list = list(scenario.scenario)
        meal_triggered = set()
        for step in range(timesteps):
            current_hour = step * 5 / 60.0
            meal_grams = 0
            for mh, grams in meal_list:
                if mh <= current_hour and (mh, grams) not in meal_triggered:
                    meal_grams += grams
                    meal_triggered.add((mh, grams))
            bg = 110 + 25 * math.sin(step/30.0) + (meal_grams * 0.5)
            log.append({'t': step, 'bg': bg, 'meal': meal_grams, 'reward': 0.0})
        bgs = [row['bg'] for row in log]
        tir = sum(1 for v in bgs if 70 <= v <= 130) / max(1, len(bgs)) * 100.0
        hypo = sum(1 for v in bgs if v < 70)
        hyper = sum(1 for v in bgs if v > 180)
        avg_bg = sum(bgs) / max(1, len(bgs))
        metrics = {
            'TIR_percent': tir,
            'Hypo_events': hypo,
            'Hyper_events': hyper,
            'Avg_BG': avg_bg,
            'Samples': len(bgs),
            'mode': 'simple-fallback',
            'fallback': True,
            'reason': 'env creation failed'
        }
        return {
            'log': log,
            'metrics': metrics,
            'start_time': scenario.start_time.isoformat(),
            'end_time': scenario.start_time.isoformat()
        }
    log = []
    meals_index = 0
    meal_list = list(scenario.scenario)  # [(hour, grams)]
    meal_triggered = set()
    for step in range(timesteps):
        # Egyszerű trigger: ha a környezet aktuális idő >= meal hour és még nem adtuk
        current_hour = info.get('time', step * 3 / 60.0)  # fallback becslés
        meal_grams = 0
        for mh, grams in meal_list:
            # A simglucose env maga kezeli a CH bevitel időpontját; itt csak logoljuk ha elérjük
            if mh <= current_hour and (mh, grams) not in meal_triggered:
                meal_grams += grams
                meal_triggered.add((mh, grams))
        # Nincs inzulin adagolás ebben az MVP-ben
        dose = 0.0
        obs, reward, terminated, truncated, info = env.step(dose)
        log.append({
            't': step,
            'bg': float(obs[0]),
            'meal': meal_grams,
            'reward': float(reward)
        })
        if terminated or truncated:
            break
    env.close()

    # Metrikák
    bgs = [row['bg'] for row in log]
    tir = sum(1 for v in bgs if 70 <= v <= 130) / max(1, len(bgs)) * 100.0
    hypo = sum(1 for v in bgs if v < 70)
    hyper = sum(1 for v in bgs if v > 180)
    avg_bg = sum(bgs) / max(1, len(bgs))
    metrics = {
        'TIR_percent': tir,
        'Hypo_events': hypo,
        'Hyper_events': hyper,
        'Avg_BG': avg_bg,
        'Samples': len(bgs)
    }

    return {
        'log': log,
        'metrics': metrics,
        'start_time': scenario.start_time.isoformat(),
        'end_time': scenario.start_time.isoformat()
    }


def run_physiologic_simulation(patient_name: str, meals: List, timesteps: int = 500) -> Dict:
    """Közelítés valódi fiziológiai válaszra anélkül, hogy a simglucose gym env működne.
    Modell:
      - Alap BG: 110 mg/dL
      - Minden étkezés CH gramm -> glükóz emelkedés impulzusa: amplitude = carbs_g * 3
      - Felszívódás: két komponens (gyors és lassú), exponenciális lecsengéssel.
      - Időlépték: 1 perc per step.
    """
    # Normalizált időpontok (ha HH:MM) - reuse earlier logic
    norm_meals = []
    for m in meals:
        ts = m.timestamp
        if 'T' not in ts and len(ts) in (5,8):
            today = datetime.utcnow().date().strftime('%Y-%m-%d')
            if len(ts) == 5:
                ts = f"{today}T{ts}:00"
            else:
                ts = f"{today}T{ts}"
        norm_meals.append((m, datetime.fromisoformat(ts)))
    if norm_meals:
        start_of_day = norm_meals[0][1].replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Előkészítés: minden meal -> aktív CH pool struktúra
    active_pools = []  # list of dict: {start: dt, fast: qty, slow: qty, carbs: grams}
    for meal_obj, dt in norm_meals:
        grams = meal_obj.carbs_g
        amplitude = grams * 3.0
        # 60% gyors, 40% lassú komponens
        active_pools.append({
            'start': dt,
            'fast': amplitude * 0.6,
            'slow': amplitude * 0.4,
            'carbs': grams
        })

    log = []
    BG = 110.0
    k_fast = 1/40.0  # gyors komponens ~40 perc felezési
    k_slow = 1/180.0 # lassú komponens ~180 perc felezési
    baseline_drift = 0.0
    for step in range(timesteps):
        current_time = start_of_day + timedelta(minutes=step)
        # Újonnan induló felszívódás jelölése
        meal_grams_this_min = 0
        # Felszívódási hatás számítás
        absorption = 0.0
        for pool in active_pools:
            elapsed_min = (current_time - pool['start']).total_seconds()/60.0
            if elapsed_min >= 0:
                # exponenciális lecsengés
                fast_contrib = pool['fast'] * (k_fast * np.exp(-k_fast * elapsed_min))
                slow_contrib = pool['slow'] * (k_slow * np.exp(-k_slow * elapsed_min))
                absorption += fast_contrib + slow_contrib
                # első percben jelöld a meal grammot (log célra)
                if 0 <= elapsed_min < 1:
                    meal_grams_this_min += pool['carbs']
        # Nincs inzulin (MVP)
        insulin_effect = 0.0
        # BG frissítés: egyszerű additív modell baseline körül
        BG = 110 + baseline_drift + absorption
        log.append({
            't': step,
            'bg': BG,
            'meal': meal_grams_this_min,
            'reward': 0.0
        })
    # Metrikák
    bgs = [row['bg'] for row in log]
    tir = sum(1 for v in bgs if 70 <= v <= 130) / max(1, len(bgs)) * 100.0
    hypo = sum(1 for v in bgs if v < 70)
    hyper = sum(1 for v in bgs if v > 180)
    avg_bg = float(np.mean(bgs)) if bgs else 0.0
    metrics = {
        'TIR_percent': tir,
        'Hypo_events': hypo,
        'Hyper_events': hyper,
        'Avg_BG': avg_bg,
        'Samples': len(bgs),
        'model': 'synthetic_absorption',
        'fallback': False
    }
    return {
        'log': log,
        'metrics': metrics,
        'start_time': start_of_day.isoformat(),
        'end_time': (start_of_day + timedelta(minutes=timesteps)).isoformat()
    }


def save_simulation_artifacts(run_id: int, data: Dict, base_dir: Path) -> Dict:
    """Mentés: log CSV + chart PNG + metrics JSON.
    base_dir: gyökér mappa (például projekt root).
    Visszaadja a fájlok relatív útvonalait.
    """
    run_dir = base_dir / f"simruns/{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    # Log CSV
    csv_path = run_dir / "log.csv"
    with open(csv_path, 'w') as f:
        f.write('t,bg,meal,reward\n')
        for row in data['log']:
            f.write(f"{row['t']},{row['bg']},{row['meal']},{row['reward']}\n")
    # Chart PNG
    chart_path = run_dir / "chart.png"
    plt.figure(figsize=(10,4))
    plt.plot([r['t'] for r in data['log']], [r['bg'] for r in data['log']], label='BG')
    # Meal markers
    for r in data['log']:
        if r['meal'] > 0:
            plt.scatter(r['t'], r['bg'], color='orange', s=40, label='Meal' if 'Meal' not in plt.gca().get_legend_handles_labels()[1] else '')
    plt.title('Blood Glucose Simulation')
    plt.xlabel('Timestep')
    plt.ylabel('BG')
    plt.legend()
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    # Metrics JSON
    metrics_path = run_dir / "metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(data['metrics'], f, indent=2)

    return {
        'log_path': str(csv_path),
        'chart_path': str(chart_path),
        'metrics_path': str(metrics_path)
    }
