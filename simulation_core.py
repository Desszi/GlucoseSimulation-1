import numpy as np
import pandas as pd
import os
import imageio
import gymnasium
import pkg_resources

from pathlib import Path
from datetime import datetime, timedelta
from PIL import ImageGrab
from random import randint
from colorama import Fore
from simglucose.simulation.scenario import CustomScenario
from gymnasium.envs.registration import register
from stable_baselines3 import A2C, TD3
from stable_baselines3.common.noise import NormalActionNoise
from stable_baselines3.common.callbacks import BaseCallback


TIMESTEPS = 500  
PATIENT_NAME = "adult#002"

# === Utility ===

def generated_day(bw, n_meals: int = 4):
    """Generál egy napnyi étkezés listát.

    Visszatér: list[list[int]] ahol elem: [CHO_gramm, start_time_perc, duration_perc].
    Eredeti 6 étkezéses statikus logikát lecseréljük egy általános  n_meals  generátorra.

    Heurisztikák:
      - Étkezések egyenletesen osztva a napban (24*60 perc) jitterrel.
      - Minden 4. nagyobb (főétkezés), többi snack.
      - CH mennyiség testtömeg (bw) alapú skálázással.
    """
    from scipy import stats
    events = []
    day_minutes = 24 * 60
    base_interval = day_minutes / n_meals

    for i in range(n_meals):
        center = (i + 0.5) * base_interval
        # idő jitter: normális eloszlás, ±20% szórás, klippelve
        t = stats.norm(loc=center, scale=base_interval * 0.2).rvs()
        t = int(round(max(0, min(day_minutes - 1, t))))

        # időtartam (meal absorption window) 5–40 perc
        h = stats.norm(loc=15, scale=5).rvs()
        h = int(round(max(5, min(40, h))))

        # CH mennyiség skálázás
        if i % 4 == 0:             # reggeli / ebéd / vacsora-szerű nagyobb
            mean_factor = 0.8 if i % 8 == 0 else 0.6
        elif i % 4 == 2:           # közepes (pl. ebéd / vacsora előtti snack)
            mean_factor = 0.4
        else:                      # kis snack
            mean_factor = 0.25

        mean_amount = bw * mean_factor
        std_amount = mean_amount * 0.20
        e = stats.norm(loc=mean_amount, scale=std_amount).rvs()
        e = int(round(max(5, e)))  # min 5g hogy ne legyen túl sok 0

        events.append([e, t, h])

    # idő szerint rendezés (bár alapból is az, jitter miatt lehet felcserélődés)
    events.sort(key=lambda x: x[1])
    return events


def get_model_path(base_dir: Path, model_name: str) -> Path:
    return base_dir / f"{model_name}.zip"


def list_model_sets(root_dir: Path = Path("TrainingModels")):
    """
    Returns all directories inside root_dir that contain valid .zip model files
    """
    valid_sets = []
    if not root_dir.exists():
        return valid_sets

    for subdir in root_dir.iterdir():
        if subdir.is_dir():
            zip_files = list(subdir.glob("*.zip"))
            if any(m.stem in {"lowmodel", "innermodel", "highmodel"} for m in zip_files):
                valid_sets.append(subdir)

    return sorted(valid_sets, key=lambda p: p.stat().st_mtime, reverse=True)  # Most recent first


def prompt_user_to_choose_model_set():
    model_sets = list_model_sets()
    if not model_sets:
        print("No trained model sets found in 'TrainingModels/'.")
        return None

    most_recent = model_sets[0] if model_sets else None

    print("\nAvailable Trained Model Sets:")
    if most_recent:
        print(f" [0] Use most recently trained model ({most_recent.name})")
    print(" [1] Choose from list")
    print(" [2] Provide a custom path manually")

    try:
        choice = int(input("Select an option: "))
        if choice == 0 and most_recent:
            return most_recent
        elif choice == 1:
            print("\nModel Sets:")
            for i, path in enumerate(model_sets):
                print(f" [{i}] {path.name}")
            sub_choice = int(input("Choose model set: "))
            if 0 <= sub_choice < len(model_sets):
                return model_sets[sub_choice]
        elif choice == 2:
            custom_path = input("Enter full path to trained model directory: ").strip()
            path_obj = Path(custom_path)
            if path_obj.exists() and path_obj.is_dir():
                return path_obj
            else:
                print("Invalid path provided.")
    except ValueError:
        print("Invalid input. Training from scratch.")

    return None


def load_model_from_file(model_path: Path, model_type: str, env):
    model_class = A2C if model_type == "A2C" else TD3
    print(f"[Model I/O] Loading model from {model_path}")
    return model_class.load(str(model_path), env=env)


def save_model(model, base_dir: Path, model_name: str):
    model_path = get_model_path(base_dir, model_name)
    model.save(str(model_path))
    print(f"[Model I/O] Saved {model_name} model to {model_path}")


def clear_console():
    os.system('cls')


# === Config ===

class SimulationConfig:
    def __init__(self, model_type="TD3"):
        self.save_to_csv = True
        # Video mentés kikapcsolva alapértelmezetten, mert a generálás közben lefagy/elhasal.
        # Kapcsold vissza ha szükséges: config.save_video = True a main-ben.
        self.save_video = False
        self.render_sim = True
        self.patient_name = PATIENT_NAME
        self.start_time = datetime(2025, 1, 1, 0, 0, 0)
        self.time_steps = TIMESTEPS
        self.max_episode_steps = 1000000
        self.model_type = model_type
        self.model_name = model_type

    def get_patient_params(self):
        patient_params_file = pkg_resources.resource_filename("simglucose", "params/vpatient_params.csv")
        patient_params = pd.read_csv(patient_params_file)
        bw = patient_params[patient_params["Name"] == self.patient_name]["BW"].iloc[0]
        return {"bw": bw}

# === Scenario Generation ===

class MealGenerator:
    def __init__(self, config: SimulationConfig):
        self.config = config

    def create_meal_scenario(self, bw):
        meal_events = generated_day(bw)
        meals = [(event[2], event[0]) for event in meal_events]
        return CustomScenario(start_time=self.config.start_time, scenario=meals), meals

    def print_meals(self, meals):
        print("CHO intakes:")
        for meal in meals:
            print(Fore.BLUE + f"   Meal: at {meal[0]} o'clock {meal[1]}g")
        print(Fore.RESET)

# === Environment Management ===

class EnvironmentManager:
    def __init__(self, config: SimulationConfig, meal_scenario):
        self.config = config
        self.base_kwargs = {
            "patient_name": config.patient_name,
            "custom_scenario": meal_scenario
        }
        self.path_to_results = self._create_results_directory()

    def _create_results_directory(self):
        base_folder = Path(f"SimResults/{self.config.model_name}_{self.config.patient_name}")
        counter = 0
        while base_folder.exists():
            counter += 1
            base_folder = Path(f"SimResults/{self.config.model_name}_{self.config.patient_name}_{counter:02d}")
        base_folder.mkdir(parents=True, exist_ok=False)
        print(f"Folder created: {base_folder.resolve()}")
        return base_folder

    def register_environments(self):
        envs = [
            ("simglucose/adolescent2-v0", "CustomT1DSimGymnaisumEnv"),
            ("simglucose/adolescent2-v0-low", "LowGlucoseEnv"),
            ("simglucose/adolescent2-v0-high", "HighGlucoseEnv"),
            ("simglucose/adolescent2-v0-inner", "InnerGlucoseEnv"),
        ]
        for env_id, entry_point in envs:
            register(id=env_id, entry_point=f"customEnviroments:{entry_point}",
                     max_episode_steps=self.config.max_episode_steps, kwargs=self.base_kwargs)

    def create_environments(self):
        render = "human" if self.config.render_sim else None
        env = gymnasium.make("simglucose/adolescent2-v0", render_mode=render)
        lowenv = gymnasium.make("simglucose/adolescent2-v0-low", render_mode=render)
        innerenv = gymnasium.make("simglucose/adolescent2-v0-inner", render_mode=render)
        highenv = gymnasium.make("simglucose/adolescent2-v0-high", render_mode=render)
        return env, lowenv, innerenv, highenv

# === Callback ===

class RewardLoggerCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.rewards = []

    def _on_step(self) -> bool:
        self.rewards.append(self.locals['rewards'][0])
        return True

    def save_to_csv(self, filename):
        pd.DataFrame({'timestep': range(1, len(self.rewards)+1), 'reward': self.rewards}).to_csv(filename, index=False)

# === Trainer ===

class ModelTrainer:
    def __init__(self, lowenv, innerenv, highenv, config: SimulationConfig):
        self.envs = {"lowmodel": lowenv, "innermodel": innerenv, "highmodel": highenv}
        self.config = config
        self.models = {}

    def train_or_load_models(self, use_existing_models=False):
        if use_existing_models:
            base_dir = prompt_user_to_choose_model_set()
            if base_dir is None:
                print("No model set selected. Training from scratch.")
                use_existing_models = False
        else:
            base_dir = Path(f"TrainingModels/{self.config.patient_name}_{self.config.model_type}_00")
            counter = 0
            while base_dir.exists():
                counter += 1
                base_dir = Path(f"TrainingModels/{self.config.model_name}_{self.config.patient_name}_{counter:02d}")
            base_dir.mkdir(parents=True, exist_ok=False)

        for model_name, env in self.envs.items():
            callback = RewardLoggerCallback()
            model = None

            if use_existing_models:
                model_path = get_model_path(base_dir, model_name)
                if model_path.exists():
                    model = load_model_from_file(model_path, self.config.model_type, env)
                    print(f"[{model_name}] loaded from {model_path}")
                else:
                    print(f"[{model_name}] not found in {base_dir}. Will train from scratch.")

            if model is None:
                print(f"Training new model: {model_name}")
                # Configure per-model training budget and exploration to help inner/high models learn
                # Give inner and high models more timesteps and a bit more action noise to encourage exploration
                per_model_steps = self.config.time_steps
                extra_multiplier = 1
                if model_name in {"innermodel", "highmodel"}:
                    extra_multiplier = 3
                per_model_steps = int(self.config.time_steps * extra_multiplier)

                if self.config.model_type == "A2C":
                    print(f"[Training] Using A2C for {model_name} with timesteps={per_model_steps}")
                    model = A2C("MlpPolicy", env, verbose=1)
                    model.learn(total_timesteps=per_model_steps, callback=callback)
                else:
                    # increase exploration sigma for inner/high models
                    base_sigma = 0.1
                    if model_name in {"innermodel", "highmodel"}:
                        base_sigma = 0.2
                    action_noise = NormalActionNoise(
                        mean=np.zeros(env.action_space.shape[-1]),
                        sigma=base_sigma * np.ones(env.action_space.shape[-1])
                    )
                    print(f"[Training] Using TD3 for {model_name} with timesteps={per_model_steps} and noise_sigma={base_sigma}")
                    model = TD3("MlpPolicy", env, action_noise=action_noise, verbose=1)
                    model.learn(total_timesteps=per_model_steps, callback=callback)
                if not use_existing_models:
                    save_model(model, base_dir, model_name)
                    callback.save_to_csv(base_dir / f"{model_name}_rewards.csv")

            self.models[model_name] = model

        clear_console()
        return self.models["lowmodel"], self.models["innermodel"], self.models["highmodel"]

# === Simulation Runner ===

class SimulationRunner:
    def __init__(self, env, lowmodel, innermodel, highmodel, config: SimulationConfig):
        self.env = env
        self.lowmodel = lowmodel
        self.innermodel = innermodel
        self.highmodel = highmodel
        self.config = config
        self.frames = []
        self.log_data = []
        self.insulin_timestamps = []
        self.insulin_history = []  # list of (time, dose) for IOB calculation

    def select_action(self, obs):
        value = obs[0]
        obs_array = np.array([obs])
        if value > 130:
            action, _ = self.highmodel.predict(obs_array, deterministic=True)
            return action, 'highmodel'
        elif 70 < value <= 130:
            action, _ = self.innermodel.predict(obs_array, deterministic=True)
            return action, 'innermodel'
        else:
            action, _ = self.lowmodel.predict(obs_array, deterministic=True)
            return action, 'lowmodel'

    def apply_insulin_rules(self, action, observation, risk, current_time):
        """Decide a safe insulin dose with IOB-based safety checks.
        - dynamic max based on recent carbs
        - enforce min interval and 3-in-2hrs rule
        - compute insulin-on-board (IOB) and limit dose to avoid hypoglycemia
        """
        BASE_MAX_DOSE = 3.5
        MAX_CAP = 10.0
        HYPO_THRESHOLD = 70
        TARGET_LOW = 70
        TARGET_HIGH = 130
        MIN_INTERVAL_MINUTES = 30  # don't give another bolus within 30 minutes unless urgent
        IOB_DECAY_HOURS = 4.0  # insulin activity duration for simple model
        ISF = 40.0  # mg/dL drop per 1 unit insulin (conservative default)
        SAFETY_MARGIN = 10.0  # don't allow predicted BG to go within this margin of TARGET_LOW

        # extract scalar from model action
        try:
            raw = float(np.array(action).ravel()[0])
        except Exception:
            raw = float(action)

        # compute recent carbs from last ~60 minutes (20 steps of 3 minutes)
        steps_window = 20
        recent_meal = 0
        if len(self.log_data) > 0:
            recent_entries = self.log_data[-steps_window:]
            for entry in recent_entries:
                recent_meal += float(entry.get("meal", 0) or 0)

        # dynamic max dose based on recent carbs (simple conversion)
        CARB_PER_UNIT = 10.0
        extra_from_carbs = recent_meal / CARB_PER_UNIT
        dynamic_max = min(MAX_CAP, BASE_MAX_DOSE + extra_from_carbs)

        # Map raw output to dose (supporting [-1,1] policies)
        if -1.0 <= raw <= 1.0:
            dose = max(0.0, (raw + 1.0) / 2.0 * dynamic_max)
        else:
            dose = max(0.0, raw)

        # apply risk multiplier
        coefficient = 1.5 * risk if risk > 1 else 1.0
        dose = dose * coefficient

        # Safety: if hypoglycemic, block
        if observation < HYPO_THRESHOLD:
            dose = 0.0

        # If BG is in target and there were no recent carbs, do not dose
        if TARGET_LOW <= observation <= TARGET_HIGH and recent_meal == 0:
            dose = 0.0

        # Enforce minimum interval since last bolus
        if self.insulin_timestamps:
            last_time = self.insulin_timestamps[-1]
            minutes_since_last = (current_time - last_time).total_seconds() / 60.0
            if minutes_since_last < MIN_INTERVAL_MINUTES:
                # allow if BG is very high (>200) or big recent meal
                if not (observation > 200 or recent_meal >= 30):
                    dose = 0.0

        # 3 injections in 2 hours safety
        two_hour_ago = current_time - timedelta(hours=2)
        self.insulin_timestamps = [t for t in self.insulin_timestamps if t > two_hour_ago]
        # also prune insulin_history
        self.insulin_history = [(t, d) for (t, d) in getattr(self, 'insulin_history', []) if t > two_hour_ago - timedelta(hours=IOB_DECAY_HOURS)]
        if len(self.insulin_timestamps) >= 3:
            print(Fore.RED + f"[Dosing Prohibited] Too many injections in last 2 hrs.")
            dose = 0.0

        # Insulin-on-board (IOB) calculation (simple linear decay)
        iob = 0.0
        for (t, d) in getattr(self, 'insulin_history', []):
            elapsed_h = (current_time - t).total_seconds() / 3600.0
            if elapsed_h < IOB_DECAY_HOURS and elapsed_h >= 0:
                remaining = max(0.0, 1.0 - (elapsed_h / IOB_DECAY_HOURS))
                iob += d * remaining
        predicted_drop_from_iob = iob * ISF

        # Determine allowable additional drop before hitting safety margin
        allowable_drop = observation - TARGET_LOW - SAFETY_MARGIN
        if allowable_drop < 0:
            allowable_drop = 0.0

        # Predict bg drop if we give the proposed dose
        predicted_drop_with_new = predicted_drop_from_iob + dose * ISF

        if predicted_drop_with_new > allowable_drop:
            # scale dose down to fit within allowable_drop
            max_additional_units = max(0.0, (allowable_drop - predicted_drop_from_iob) / ISF)
            dose = min(dose, max_additional_units)
            # If after scaling dose is negligible, set to zero
            if dose < 1e-3:
                dose = 0.0

        # Cap dose to dynamic max
        dose = min(dose, dynamic_max)

        # record if dosing
        if dose > 0:
            self.insulin_timestamps.append(current_time)
            # append to insulin_history for IOB tracking
            if not hasattr(self, 'insulin_history'):
                self.insulin_history = []
            self.insulin_history.append((current_time, dose))
            print(Fore.YELLOW + f"Injected insulin at {current_time.strftime('%H:%M')} (dose={dose:.2f}, recent_carbs={recent_meal})")

        # Debug (commented): raw, dose, bg, recent_meal, iob
        # print(Fore.CYAN + f"[DEBUG] raw={raw:.3f} dose={dose:.3f} bg={observation} recent_meal={recent_meal} iob={iob:.3f}")

        return dose

    def run(self):
        obs, info = self.env.reset()
        risk = 0
        current_time = self.config.start_time
        end_time = current_time + timedelta(hours=24)
        truncated = False

        while current_time < end_time and not truncated:
            if self.config.render_sim:
                self.env.render()
            if self.config.save_video:
                screen = ImageGrab.grab()
                self.frames.append(np.array(screen))

            current_time += timedelta(minutes=3)
            action, selected_model = self.select_action(obs)
            raw_action = float(np.array(action).ravel()[0]) if hasattr(action, '__iter__') or isinstance(action, np.ndarray) else float(action)
            dose = self.apply_insulin_rules(action, obs[0], risk, current_time)
            obs, reward, terminated, truncated, info = self.env.step(dose)
            risk = info.get("risk", 0)

            self.log_data.append({
                "selected_model": selected_model,
                "raw_action": raw_action,
                "dose": dose,
                "blood glucose": obs[0],
                "reward": reward,
                "meal": info.get("meal", 0),
                "risk": risk,
                "time": current_time.strftime("%H:%M")
            })

        # After run, produce a small summary of model selection and dosing
        try:
            df = pd.DataFrame(self.log_data)
            summary = {}
            for m in ['lowmodel', 'innermodel', 'highmodel']:
                subset = df[df['selected_model'] == m]
                if subset.empty:
                    summary[m] = {'count': 0}
                    continue
                summary[m] = {
                    'count': int(len(subset)),
                    'nonzero_doses': int((subset['dose'] > 0).sum()),
                    'raw_action_mean': float(subset['raw_action'].mean()),
                    'raw_action_std': float(subset['raw_action'].std()),
                    'dose_mean': float(subset['dose'].mean()),
                    'dose_std': float(subset['dose'].std())
                }
            out_path = getattr(self, 'env', None)
            # try to save under path_to_results if available
            try:
                import json
                path = getattr(self, 'path_to_results', None)
                if path is not None:
                    with open(path / 'model_selection_summary.json', 'w') as f:
                        json.dump(summary, f, indent=2)
                    print(Fore.GREEN + f"Saved model selection summary to {path / 'model_selection_summary.json'}")
            except Exception:
                pass
        except Exception:
            pass

        return self.frames, self.log_data

# === Data Saving ===

class DataSaver:
    def __init__(self, path: Path, config: SimulationConfig):
        self.path = path
        self.config = config

    def save_csv(self, data, filename="LogData.csv"):
        if self.config.save_to_csv:
            df = pd.DataFrame(data)
            df.to_csv(self.path / filename, index=False)
            print(Fore.GREEN + f"Saved CSV: {self.path / filename}")

    def save_video(self, frames, filename="Simulation.mp4"):
        if self.config.save_video:
            print(Fore.YELLOW + "Saving video... this may take a moment.")
            imageio.mimsave(self.path / filename, frames, fps=20)
            print(Fore.GREEN + f"Saved video: {self.path / filename}")

# === Metrics ===

class MetricsCalculator:
    def __init__(self, path: Path):
        self.path = path

    def calculate(self, log_data):
        df = pd.DataFrame(log_data)
        tir = ((df["blood glucose"] >= 70) & (df["blood glucose"] <= 130)).mean() * 100
        hypo = (df["blood glucose"] < 70).sum()
        hyper = (df["blood glucose"] > 180).sum()
        mean_risk = df["risk"].mean()
        avg_reward = df["reward"].mean()
        return {
            "TIR (%)": tir,
            "Hypo Events": hypo,
            "Hyper Events": hyper,
            "Mean Risk": mean_risk,
            "Average Reward": avg_reward
        }

    def save(self, metrics, filename="metrics.txt"):
        with open(self.path / filename, "w") as f:
            for k, v in metrics.items():
                f.write(f"{k}: {v:.2f}\n")
        print(Fore.GREEN + f"Saved metrics: {self.path / filename}")
