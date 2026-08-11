"""Compatibility wrapper for the writer-first dashboard and companion views."""
from .workspace import generate
from .explore import generate_explore
from .analysis_view import generate_analysis_view


def generate_all():
    """Generate the main workspace plus writer-focused companion views."""
    path = generate()
    generate_explore()
    generate_analysis_view()
    return path


__all__ = ["generate_all"]
