"""Dashboard package — HTML report generation."""
from .generator import generate
from .file_viewer import generate as generate_files, generate_single_file_reader

__all__ = ["generate", "generate_files", "generate_single_file_reader"]
