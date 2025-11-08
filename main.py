from simulation_core import (
    SimulationConfig, MealGenerator, EnvironmentManager,
    ModelTrainer, SimulationRunner, DataSaver, MetricsCalculator
)

# === Main Entry Point ===
def main():
    # Setup Config 
    config = SimulationConfig(model_type="PPO")
    patient_params = config.get_patient_params()
    print(f"Patient {config.patient_name} | BW: {patient_params['bw']} kg")

    # Generate Meals
    meal_gen = MealGenerator(config)
    scenario, meals = meal_gen.create_meal_scenario(patient_params["bw"])
    meal_gen.print_meals(meals)

    # Manage Enviroments
    env_mgr = EnvironmentManager(config, scenario)
    env_mgr.register_environments()
    env, lowenv, innerenv, highenv = env_mgr.create_environments()

    # Train Models
    trainer = ModelTrainer(lowenv, innerenv, highenv, config)
    lowmodel, innermodel, highmodel = trainer.train_or_load_models(use_existing_models=False)

    # Run the simulation
    runner = SimulationRunner(env, lowmodel, innermodel, highmodel, config)
    frames, log_data = runner.run()

    # Optional: run SHAP analysis if shap installed and helper available
    try:
        from analysis.shap_helper import run_shap_analysis
        from analysis.critical_shap import analyze_critical_shap
        
        # Run SHAP for each of the three specialization models
        for m, name in [(lowmodel, 'lowmodel'), (innermodel, 'innermodel'), (highmodel, 'highmodel')]:
            try:
                print(f"[Main] Running SHAP analysis on {name}...")
                run_shap_analysis(m, log_data, env_mgr.path_to_results, model_name=name)
                
                print(f"[Main] Running Critical SHAP analysis on {name}...")
                analyze_critical_shap(m, log_data, env_mgr.path_to_results, model_name=name)
                
            except Exception as e:
                print(f"[Main] SHAP for {name} skipped: {e}")
    except Exception as e:
        print(f"[Main] SHAP analysis skipped entirely: {e}")

    # Save Result and metrics
    saver = DataSaver(env_mgr.path_to_results, config)
    saver.save_csv(log_data)
    saver.save_video(frames)

    metrics_calc = MetricsCalculator(env_mgr.path_to_results)
    metrics = metrics_calc.calculate(log_data)
    metrics_calc.save(metrics)

    # --- Auto-generate WMA visualization plot if LogData.csv exists ---
    try:
        from pathlib import Path
        from analysis.wma_visualization import main as wma_plot_main
        log_csv_path = Path(env_mgr.path_to_results) / 'LogData.csv'
        if log_csv_path.exists():
            print('[Main] Generating WMA plot...')
            wma_plot_main(log_csv_path)
        else:
            print(f'[Main] LogData.csv not found at {log_csv_path}, skipping WMA plot.')
    except Exception as e:
        print(f'[Main] WMA plot generation skipped due to error: {e}')

    # --- Auto-generate Critical Events Stats visualization ---
    try:
        from analysis.critical_events_viz import main as critical_viz_main
        print('[Main] Generating Critical Events visualization...')
        critical_viz_main(env_mgr.path_to_results)
    except Exception as e:
        print(f'[Main] Critical Events visualization skipped due to error: {e}')

    # --- Auto-generate Critical Events Timeline visualization ---
    try:
        from analysis.critical_timeline import main as critical_timeline_main
        print('[Main] Generating Critical Events timeline plots...')
        critical_timeline_main(env_mgr.path_to_results)
    except Exception as e:
        print(f'[Main] Critical Events timeline skipped due to error: {e}')

    env.close()


if __name__ == "__main__":
    main()
