"""Dashboard and writer workspace views."""
from .generator import generate_all

# Keep the existing public generate() entry point used by the CLI.
generate = generate_all

__all__ = ["generate", "generate_all"]
