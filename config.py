"""
AgenticCyOps — Project Configuration

Single source of truth for base paths. All modules import from here
instead of hardcoding /storage/data/AgenticCyOps_Private.

Usage:
    from config import BASE_DIR, MODELS_DIR, LOGS_DIR, load_env

    # Paths
    manifest = BASE_DIR / "configs" / "admin_manifest.json"
    model = MODELS_DIR / "Qwen" / "Qwen3-235B-A22B-Instruct-2507"

    # Load .env
    load_env()
"""

from pathlib import Path

# Project root — derived from this file's location
BASE_DIR = Path(__file__).resolve().parent

# Key subdirectories
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
CONFIGS_DIR = BASE_DIR / "configs"


def load_env():
    """Load .env file from project root if it exists."""
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
