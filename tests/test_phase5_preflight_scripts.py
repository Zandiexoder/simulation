import os


def test_pretesting_scripts_exist_and_executable():
    for p in ['scripts/preflight.sh', 'scripts/smoke_run.sh', 'scripts/benchmark_tick.sh', 'scripts/test_all.sh', 'scripts/run_benchmarks.sh', 'scripts/run_soak.sh', 'scripts/run_scenario_matrix.sh', 'scripts/run_tuning_matrix.sh', 'scripts/generate_readiness_report.sh']:
        assert os.path.exists(p)
        assert os.access(p, os.X_OK)
