"""PySide6 monitoring dashboard for Prince."""

__all__ = ["MonitoringDashboard"]


def __getattr__(name):
    if name == "MonitoringDashboard":
        from .window import MonitoringDashboard
        return MonitoringDashboard
    raise AttributeError(name)
