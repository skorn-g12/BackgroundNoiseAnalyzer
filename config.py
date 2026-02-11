"""Configuration: categories, paths, sample rate, level range, max duration."""
from pathlib import Path

# Root directory (shivani/BackgroundNoise)
ROOT_DIR = Path(__file__).resolve().parent
RAW_DIR = ROOT_DIR / "raw"
LEVELS_DIR = ROOT_DIR / "levels"
MANIFEST_ORIGINAL_CSV = ROOT_DIR / "manifest_original.csv"
SURVEY_MAPPING_CSV = ROOT_DIR / "survey_mapping.csv"
COLLECTED_RESPONSES_CSV = ROOT_DIR / "collected_responses.csv"

# Categories: 5 samples each
CATEGORIES = [
    "Office",
    "Cafe",
    "StreetTraffic",
    "Home",
    "CallCenter",
    "Construction",
    "Airport",
]

# Audio
SAMPLE_RATE = 16000
MAX_DURATION_SEC = 100.0

# Intensity levels: -40 dB to -10 dB, step 5 dB → 7 levels
LEVEL_DB_MIN = -40
LEVEL_DB_MAX = -10
LEVEL_DB_STEP = 5
LEVELS_DB = list(range(LEVEL_DB_MIN, LEVEL_DB_MAX + 1, LEVEL_DB_STEP))
# [-40, -35, -30, -25, -20, -15, -10]

SAMPLES_PER_CATEGORY = 5
AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg")
