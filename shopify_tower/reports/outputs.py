"""
Generate CSV report files for low_stock, reorder_list, and dead_stock.
"""
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

from config.settings import REPORTS_DIR
from metrics.flags import get_low_stock, get_reorder_list, get_dead_stock

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(REPORTS_DIR)


def _ensure_dir():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _write_csv(filename: str, rows: list[dict], fieldnames: list[str]) -> Path:
    path = REPORTS_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Report written: %s (%d rows)", path, len(rows))
    return path


def generate_low_stock_report(metrics: list[dict] = None) -> Path:
    _ensure_dir()
    rows = get_low_stock(metrics)
    fields = [
        "sku", "product_title", "variant_title",
        "total_available", "velocity_per_day", "days_of_stock", "flag",
    ]
    return _write_csv(f"low_stock_{_today()}.csv", rows, fields)


def generate_reorder_report(metrics: list[dict] = None) -> Path:
    _ensure_dir()
    rows = get_reorder_list(metrics)
    fields = [
        "sku", "product_title", "variant_title",
        "total_available", "velocity_per_day", "days_of_stock",
        "reorder_qty", "flag",
    ]
    return _write_csv(f"reorder_list_{_today()}.csv", rows, fields)


def generate_dead_stock_report(metrics: list[dict] = None) -> Path:
    _ensure_dir()
    rows = get_dead_stock(metrics)
    fields = [
        "sku", "product_title", "variant_title",
        "total_available", "sold_7d", "sold_14d", "sold_30d", "flag",
    ]
    return _write_csv(f"dead_stock_{_today()}.csv", rows, fields)


def generate_all_reports(metrics: list[dict] = None) -> dict:
    """Generate all 3 reports and return their paths."""
    from metrics.compute import compute_metrics
    m = metrics or compute_metrics()
    return {
        "low_stock":  generate_low_stock_report(m),
        "reorder":    generate_reorder_report(m),
        "dead_stock": generate_dead_stock_report(m),
    }
