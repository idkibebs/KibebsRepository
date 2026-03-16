"""
Central configuration for Shopify Inventory Control Tower.
All secrets come from environment variables via .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ── Shopify ──────────────────────────────────────────────────────────────────
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")        # e.g. mystore.myshopify.com
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")  # Admin API token
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")

# ── Database ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "db" / "inventory.db"))

# ── Inventory thresholds ─────────────────────────────────────────────────────
CRITICAL_DAYS = 7       # < 7 days stock → Critical
LOW_DAYS = 14           # 7–14 days → Low
DEAD_STOCK_DAYS = 60    # > 60 days stock with no sales → Dead Stock
REORDER_TARGET_DAYS = 30  # How many days of coverage to reorder toward
VELOCITY_WINDOW_DAYS = 30  # Days to look back for velocity calc

# ── Reporting ────────────────────────────────────────────────────────────────
REPORTS_DIR = BASE_DIR / "reports" / "output"
LOGS_DIR = BASE_DIR / "logs"

# ── Scheduler ────────────────────────────────────────────────────────────────
SYNC_HOUR = int(os.getenv("SYNC_HOUR", "3"))    # 3 AM daily sync
SYNC_MINUTE = int(os.getenv("SYNC_MINUTE", "0"))

# ── Shopify rate limits ───────────────────────────────────────────────────────
API_RATE_LIMIT_SLEEP = 0.5   # seconds between paginated requests
MAX_RETRIES = 5
RETRY_BACKOFF = 2            # exponential backoff base (seconds)
