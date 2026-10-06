"""Experiment runner exceptions."""


class RunnerError(RuntimeError):
    """Base error for experiment orchestration."""


class PreflightError(RunnerError):
    """Preflight validation failed."""


class ExperimentInterruptedError(RunnerError):
    """Run interrupted by signal or user."""
