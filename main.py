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
        # Run SHAP for each of the three specialization models
        for m, name in [(lowmodel, 'lowmodel'), (innermodel, 'innermodel'), (highmodel, 'highmodel')]:
            try:
                print(f"[Main] Running SHAP analysis on {name}...")
                run_shap_analysis(m, log_data, env_mgr.path_to_results, model_name=name)
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

    env.close()


if __name__ == "__main__":
    main()
