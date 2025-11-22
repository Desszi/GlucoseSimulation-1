from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from sqlmodel import Session, select
from ...core.database import get_session
from ...models.user import User, UserRole
from ...models.patient import Patient
from ...models.meal import Meal
from ...models.simulation import SimulationRun
from ...schemas.simulation import SimulationRunCreate, SimulationRunRead
from datetime import datetime
import json
from pathlib import Path
from ...services.simulation_runner import run_simple_simulation, run_physiologic_simulation, save_simulation_artifacts
from ..deps import get_current_user
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/run", response_model=SimulationRunRead)
def run_sim(data: SimulationRunCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    patient = session.exec(select(Patient).where(Patient.user_id == current_user.id)).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile missing")
    # Meal kiválasztás: ha nincs megadva vagy üres lista -> összes étkezés a beteghez
    if not data.meal_ids:
        meals = session.exec(select(Meal).where(Meal.patient_id == patient.id)).all()
    else:
        meals = session.exec(select(Meal).where(Meal.id.in_(data.meal_ids))).all()
    # ensure meals belong to this patient
    for m in meals:
        if m.patient_id != patient.id:
            raise HTTPException(status_code=400, detail="Meal does not belong to patient")
    # Valódi (egyszerű) futtatás – csak null inzulin, metrikák + chart
    steps = data.timesteps or 500
    if data.full_day:
        # 24 órás: 1 perc / lépés logikára állunk (synthetic model jelenleg perc alapú). 24*60 = 1440
        steps = 1440
    logger.info(f"Simulation run start patient_id={patient.id} steps={steps} meal_count={len(meals)} meal_ids={[m.id for m in meals]}")
    mode = (data.mode or 'simple').lower()
    try:
        if mode == 'physio':
            sim_data = run_physiologic_simulation(patient_name=patient.full_name or patient.taj or "patient", meals=meals, timesteps=steps)
        else:
            sim_data = run_simple_simulation(patient_name=patient.full_name or patient.taj or "patient", meals=meals, timesteps=steps)
        # Extra metrikák számítása
        log_rows = sim_data.get('log', [])
        bgs = [r['bg'] for r in log_rows]
        if bgs:
            peak_bg = max(bgs)
            time_to_peak = bgs.index(peak_bg)  # perces lépés
            # Szórás
            import math
            mean_bg = sum(bgs)/len(bgs)
            variance = sum((x-mean_bg)**2 for x in bgs)/len(bgs)
            stddev = math.sqrt(variance)
            # Egyszerű AUC: összeg (perces lépések miatt mg/dL*min)
            auc = sum(bgs)
            sim_data['metrics'].update({
                'Peak_BG': peak_bg,
                'Time_to_Peak_min': time_to_peak,
                'StdDev_BG': stddev,
                'AUC_BG': auc
            })
    except Exception as e:
        logger.exception("Simulation run failed")
        raise HTTPException(status_code=500, detail=f"Simulation error: {type(e).__name__}: {e}")
    logger.info(f"Simulation run success patient_id={patient.id} samples={len(sim_data.get('log', []))}")

    now = datetime.utcnow().isoformat()
    sim = SimulationRun(
        patient_id=patient.id,
        created_at=now,
        started_at=now,
        finished_at=now,
        input_meals=json.dumps([m.id for m in meals]),
        result_metrics=json.dumps(sim_data['metrics']),
        chart_path="",
        log_path=""
    )
    session.add(sim)
    session.commit()
    session.refresh(sim)

    # Artefaktum mentés (projekt root). A fájl elérési útja:
    #   <repo>/backend/app/api/routes/simulation.py
    # parents indexek: 0=routes,1=api,2=app,3=backend,4=<repo root>
    # A repo gyökér a parents[4], de a backend gyökér is elegendő nekünk a simruns létrehozásához.
    # Használjuk inkább a valódi repo gyökeret (parents[4]) ha létezik, különben fallback a backend mappára.
    file_parents = Path(__file__).resolve().parents
    root_dir = file_parents[4] if len(file_parents) >= 5 else file_parents[3]
    paths = save_simulation_artifacts(run_id=sim.id, data=sim_data, base_dir=root_dir)
    sim.chart_path = paths['chart_path']
    sim.log_path = paths['log_path']
    session.add(sim)
    session.commit()
    session.refresh(sim)
    return sim

@router.post("/rl")
def run_rl(meals: list[dict], session: Session = Depends(get_session), current_user: User = Depends(get_current_user), force_train: bool = False):
    """24 órás RL szimuláció a UI által megadott étkezésekkel.
    Body: list[{timestamp: 'HH:MM' vagy ISO, carbs_g: int}]
    Query: force_train.
    A modell típusa mindig PPO (main.py konzisztencia), felhasználó nem választhat algoritmust.
    Lazy import a nehéz RL modulra, így a backend elindul akkor is, ha a RL függőségek még nincsenek telepítve."""
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    try:
        from ...services.rl_simulation import run_rl_full_day  # lazy import
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RL module import failed: {type(e).__name__}: {e}")
    try:
        result = run_rl_full_day(meals, force_train=force_train)
    except Exception as e:
        logger.exception("RL simulation failed")
        raise HTTPException(status_code=500, detail=f"RL simulation error: {type(e).__name__}: {e}")
    return result

@router.get("/runs", response_model=list[SimulationRunRead])
def list_runs(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Not a patient user")
    patient = session.exec(select(Patient).where(Patient.user_id == current_user.id)).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient missing")
    runs = session.exec(select(SimulationRun).where(SimulationRun.patient_id == patient.id).order_by(SimulationRun.created_at.desc())).all()
    return runs

@router.get("/runs/{run_id}", response_model=SimulationRunRead)
def get_run(run_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    sim = session.get(SimulationRun, run_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Run not found")
    patient = session.exec(select(Patient).where(Patient.user_id == current_user.id)).first()
    if not patient or sim.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return sim

@router.get("/runs/{run_id}/chart")
def get_run_chart(run_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    sim = session.get(SimulationRun, run_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Run not found")
    patient = session.exec(select(Patient).where(Patient.user_id == current_user.id)).first()
    if not patient or sim.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not sim.chart_path or not Path(sim.chart_path).exists():
        raise HTTPException(status_code=404, detail="Chart missing")
    return FileResponse(sim.chart_path, media_type="image/png")
