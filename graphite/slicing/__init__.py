"""Graphite slicing and support structure processing modules."""

def __getattr__(name: str):
    if name in (
        "SupportedMeshSeparator",
        "split_supported_mesh",
        "extract_support_tips",
        "detect_and_disconnect_support_tops",
    ):
        from . import support_separator
        return getattr(support_separator, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "SupportedMeshSeparator",
    "split_supported_mesh",
    "extract_support_tips",
    "detect_and_disconnect_support_tops",
]
