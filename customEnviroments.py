from pathlib import Path
from PIL import ImageGrab
import imageio
import time
import numpy as np
import gymnasium
from gymnasium.envs.registration import register
from simglucose.simulation.scenario import CustomScenario
from datetime import datetime
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from simglucose.envs import T1DSimGymnaisumEnv
from datetime import datetime, timedelta

class CustomT1DSimGymnaisumEnv(T1DSimGymnaisumEnv):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_time = datetime(2025, 1, 1, 0, 0, 0)#Szimuláció kezdő ideje éjfél
        self.last_bg = None  # trend számításhoz
        self.bg_history = []  # vércukor értékek sorozata mozgóátlaghoz

    def _weighted_moving_average(self, history, window):
        """Lineárisan növekvő súlyokkal WMA. Ha nincs elég adat, visszaadja az aktuális BG-t."""
        if len(history) < window:
            return history[-1] if history else 0.0
        segment = history[-window:]
        weights = np.arange(1, window + 1, dtype=float)
        return float(np.dot(segment, weights) / weights.sum())

    def step(self, action):
        observation, reward, terminated, truncated, info = super().step(action)
        blood_glucose = observation[0]  
        target_bg = 120  
        bg_tolerance = 20         
        self.current_time += timedelta(minutes=3)
        deviation = abs(blood_glucose - target_bg)

        # --- Glükóz trend + egyszerű előrejelzés ---
        slope = 0.0
        if self.last_bg is not None:
            slope = blood_glucose - self.last_bg  # mg/dL / 3 perc
        self.last_bg = blood_glucose
        # 36 perces (12 lépés) előrevetítés csak pozitív slope esetén
        horizon_steps = 12
        predicted_peak = blood_glucose + max(0.0, slope) * horizon_steps
        # Dinamikus emelkedés küszöbök (konzervatív kezdet) – a későbbi CH logikához előkészítés
        mild_thr = 2.0
        fast_thr = 5.0

        # --- Súlyozott mozgó átlagok ---
        self.bg_history.append(blood_glucose)
        if len(self.bg_history) > 500:  # korlátozás memória védelemre
            self.bg_history.pop(0)
        wma5 = self._weighted_moving_average(self.bg_history, 5)
        wma10 = self._weighted_moving_average(self.bg_history, 10)
        # WMA alapú slope becslés (lassabb, simább trend)
        slope_wma5 = 0.0
        if len(self.bg_history) >= 6:
            prev_wma5 = self._weighted_moving_average(self.bg_history[:-1], 5)
            slope_wma5 = wma5 - prev_wma5
        # Alternatív predicted peak WMA-val: átlag a nyers és a simított előrejelzés között
        predicted_peak_wma = wma5 + max(0.0, slope_wma5) * horizon_steps
        blended_peak = 0.5 * predicted_peak + 0.5 * predicted_peak_wma

        #00:00 és 06:00 közötti szigorúbb bünti       
        if self.current_time.hour < 6:
            if blood_glucose > 160:
                reward -=15
            elif 100 <= blood_glucose <=150:
                reward += 7
        
        if blood_glucose > target_bg + bg_tolerance:
            reward -= 5 * (deviation / 10) 
        elif blood_glucose < target_bg - bg_tolerance:
            reward -= 5 * (deviation / 10) 
        else:
            reward += 5 

            if hasattr(self, 'last_blood_glucose'):
                fluctuation = abs(blood_glucose - self.last_blood_glucose)
                if fluctuation < 10: 
                    reward += 2  
                elif fluctuation >= 10 and fluctuation < 20:  
                    reward -= 1  
            
            self.last_blood_glucose = blood_glucose

        # --- Prediktív anticipációs jutalom / késlekedés bünti ---
        anticip_bonus = 0.0
        delay_penalty = 0.0
        # Ha várható, hogy a következő ~36 percben 180 fölé menne, jutalmazzuk az inzulint
        # Anticipáció és késlekedés a BLENDED peak alapján (stabilabb jel)
        if blended_peak > 180:
            # Ha akár a nyers slope, akár a simított slope meghaladja a mild_thr-t
            if (slope > mild_thr or slope_wma5 > mild_thr) and action > 0:
                anticip_bonus = 3.0
            # Gyors emelkedés (nyers) + nincs akció -> bünti
            if slope > fast_thr and action == 0:
                delay_penalty = -4.0
        reward += anticip_bonus + delay_penalty

        print(
            f"[{self.current_time.strftime('%H:%M')}] BG:{blood_glucose:.1f} "
            f"Reward:{reward:.2f} Slope:{slope:.1f} WMA5:{wma5:.1f} WMA10:{wma10:.1f} "
            f"PredPeakRaw:{predicted_peak:.1f} PredPeakWMA:{predicted_peak_wma:.1f} Blend:{blended_peak:.1f} "
            f"Ant:{anticip_bonus:.1f} Del:{delay_penalty:.1f}"
        )

        return observation, reward, terminated, truncated, info
 
class LowGlucoseEnv(T1DSimGymnaisumEnv):
    def step(self, action):
        observation, reward, terminated, truncated, info = super().step(action)
        blood_glucose = observation[0]
        
        # Target range: 70–180 mg/dL, with emphasis on avoiding hypoglycemia (<70)
        target_bg = 120  # Ideal glucose level
        bg_tolerance = 20  # Tolerance around target (100–140 mg/dL)
        
        # Base reward for staying in safe range
        if 70 <= blood_glucose <= 180:
            reward += 50 - 0.2 * (blood_glucose - target_bg) ** 2  # Quadratic reward, max at 120
        elif blood_glucose < 70:
            deviation = 70 - blood_glucose
            reward -= 20 * (deviation / 10)  # Linear penalty for hypoglycemia
        else:  # blood_glucose > 180
            deviation = blood_glucose - 180
            reward -= 10 * (deviation / 20)  # Mild penalty for hyperglycemia
        
        # Penalize high insulin during low glucose
        if action > 0.3 and blood_glucose < 70:
            reward -= 15  # Reduced penalty, only for significant insulin
        
        # Reward smooth glucose transitions
        if hasattr(self, 'last_blood_glucose'):
            fluctuation = abs(blood_glucose - self.last_blood_glucose)
            if fluctuation < 5:
                reward += 5  # Bonus for stability
            elif fluctuation > 15:
                reward -= 5  # Penalty for large swings
        
        self.last_blood_glucose = blood_glucose
        
        return observation, reward, terminated, truncated, info

class HighGlucoseEnv(T1DSimGymnaisumEnv):
    def step(self, action):
        observation, reward, terminated, truncated, info = super().step(action)
        blood_glucose = observation[0]
        
        # Target range: 70–180 mg/dL, with emphasis on avoiding hyperglycemia (>180)
        target_bg = 120
        bg_tolerance = 20
        
        # Base reward for staying in safe range
        if 70 <= blood_glucose <= 180:
            reward += 50 - 0.2 * (blood_glucose - target_bg) ** 2  # Quadratic reward, max at 120
        elif blood_glucose > 180:
            deviation = blood_glucose - 180
            reward -= 20 * (deviation / 20)  # Linear penalty for hyperglycemia
        else:  # blood_glucose < 70
            deviation = 70 - blood_glucose
            reward -= 10 * (deviation / 10)  # Mild penalty for hypoglycemia
        
        # Penalize high insulin during low glucose
        if action > 0.3 and blood_glucose < 70:
            reward -= 15  # Reduced penalty, only for significant insulin
        
        # Reward smooth glucose transitions
        if hasattr(self, 'last_blood_glucose'):
            fluctuation = abs(blood_glucose - self.last_blood_glucose)
            if fluctuation < 5:
                reward += 5  # Bonus for stability
            elif fluctuation > 15:
                reward -= 5  # Penalty for large swings
        
        self.last_blood_glucose = blood_glucose
        
        return observation, reward, terminated, truncated, info

class InnerGlucoseEnv(T1DSimGymnaisumEnv):
    def step(self, action):
        observation, reward, terminated, truncated, info = super().step(action)
        blood_glucose = observation[0]
        
        # Target range: 70–130 mg/dL, with emphasis on tight control
        target_bg = 100  # Tighter target for inner range
        bg_tolerance = 15  # Narrower tolerance (85–115 mg/dL)
        
        # Base reward for staying in tight range
        if 70 <= blood_glucose <= 130:
            reward += 60 - 0.3 * (blood_glucose - target_bg) ** 2  # Higher reward, max at 100
        elif blood_glucose < 70:
            deviation = 70 - blood_glucose
            reward -= 15 * (deviation / 10)  # Reduced penalty for hypoglycemia
        else:  # blood_glucose > 130
            deviation = blood_glucose - 130
            reward -= 10 * (deviation / 20)  # Mild penalty for exceeding 130
        
        # Penalize high insulin doses to encourage conservative dosing
        if action > 0.3:
            reward -= 5  # Mild penalty for high insulin
        
        # Reward smooth glucose transitions
        if hasattr(self, 'last_blood_glucose'):
            fluctuation = abs(blood_glucose - self.last_blood_glucose)
            if fluctuation < 5:
                reward += 5  # Bonus for stability
            elif fluctuation > 15:
                reward -= 5  # Penalty for large swings
        
        self.last_blood_glucose = blood_glucose
        
        return observation, reward, terminated, truncated, info
    