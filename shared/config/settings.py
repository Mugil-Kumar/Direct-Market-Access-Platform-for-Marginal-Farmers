import os


APP_NAME = "AGRIWEAVE"

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./agriweave.db"
)

DEFAULT_PLATFORM_FEE_PERCENT = 2.0
DEFAULT_SPOILAGE_PERCENT = 2.0
DEFAULT_MAX_MATCH_DISTANCE_KM = 100.0
