"""Monitor de desempenho respeita performance_metrics.enabled."""

from __future__ import annotations

from modules.experiment.stages.metrics import CombinationPerformanceMonitor


def test_disabled_monitor_does_not_record_phases() -> None:
    monitor = CombinationPerformanceMonitor(
        device="cpu",
        timezone_name="UTC",
        settings={"enabled": False},
    )
    monitor.start()
    with monitor.measure_load():
        pass
    with monitor.measure_inference(text_count=3):
        pass
    snapshot = monitor.stop()

    assert monitor.enabled is False
    assert snapshot.phases == ()
    assert snapshot.load_time_seconds is None
    assert snapshot.inference_time_seconds is None
    assert snapshot.total_time_seconds == 0.0


def test_enabled_monitor_records_load_phase() -> None:
    monitor = CombinationPerformanceMonitor(
        device="cpu",
        timezone_name="UTC",
        settings={"enabled": True},
    )
    monitor.start()
    with monitor.measure_load():
        pass
    snapshot = monitor.stop()
    assert any(phase.name == "load" for phase in snapshot.phases)
    assert snapshot.load_time_seconds is not None
