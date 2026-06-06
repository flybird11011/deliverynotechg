"""Packaged application entry point for PyInstaller."""

from src.deliverynotechg.pipeline import main as run_pipeline


if __name__ == "__main__":
    run_pipeline()
