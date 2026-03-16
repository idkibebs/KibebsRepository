"""
Compute per-variant inventory metrics from the local database.

Metrics produced per variant:
  - units_sold_7d / 14d / 30d
  - velocity_per_day  (units/day over VELOCITY_WINDOW_DAYS)
  - total_available   (sum across all locations)
  - days_of_stock     (total_available / velocity, ∞ if velocity==0)
  - reorder_qty       (units needed to reach REORDER_TARGET_DAYS of coverage)
  - flag              (OK | Low | Critical | Dead Stock)
"""
import logging
from datetime import datetime, timedelta, timezone

from db.database import db_conn
from config.settings import (
    CRITICAL_DAYS,
    LOW_DAYS,
    DEAD_STOCK_DAYS,
    REORDER_TARGET_DAYS,
    VELOCITY_WINDOW_DAYS,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _sold_in_window(conn, variant_id: str, days: int) -> int:
    cutoff = (_now_utc() - timedelta(days=days)).isoformat()
    row = conn.execute(
        """SELECT COALESCE(SUM(oi.quantity), 0) AS sold
           FROM order_items oi
           JOIN orders o ON o.id = oi.order_id
           WHERE oi.variant_id = ?
             AND o.created_at >= ?
             AND o.financial_status NOT IN ('refunded', 'voided')""",
        (variant_id, cutoff),
    ).fetchone()
    return int(row["sold"])


def compute_metrics() -> list[dict]:
    """
    Return a list of metric dicts, one per variant.
    Aggregates inventory across all locations.
    """
    with db_conn() as conn:
        variants = conn.execute("SELECT * FROM variants").fetchall()
        results = []

        for v in variants:
            vid = v["id"]

            # ── Inventory: sum across locations ──────────────────────────────
            inv_row = conn.execute(
                "SELECT COALESCE(SUM(available), 0) AS total FROM inventory_levels WHERE variant_id=?",
                (vid,),
            ).fetchone()
            total_available = int(inv_row["total"])

            # ── Sales windows ─────────────────────────────────────────────────
            sold_7d  = _sold_in_window(conn, vid, 7)
            sold_14d = _sold_in_window(conn, vid, 14)
            sold_30d = _sold_in_window(conn, vid, VELOCITY_WINDOW_DAYS)

            # ── Velocity (units/day) ──────────────────────────────────────────
            velocity = round(sold_30d / VELOCITY_WINDOW_DAYS, 4)

            # ── Days of stock left ────────────────────────────────────────────
            if velocity > 0:
                days_of_stock = round(total_available / velocity, 1)
            else:
                days_of_stock = float("inf")  # no sales → treat as infinite

            # ── Reorder quantity ──────────────────────────────────────────────
            if velocity > 0:
                ideal_stock = velocity * REORDER_TARGET_DAYS
                reorder_qty = max(0, round(ideal_stock - total_available))
            else:
                reorder_qty = 0

            # ── Flag ──────────────────────────────────────────────────────────
            flag = _assign_flag(total_available, days_of_stock, sold_30d)

            results.append(
                {
                    "variant_id":       vid,
                    "sku":              v["sku"],
                    "product_title":    v["product_title"],
                    "variant_title":    v["title"],
                    "price":            v["price"],
                    "total_available":  total_available,
                    "sold_7d":          sold_7d,
                    "sold_14d":         sold_14d,
                    "sold_30d":         sold_30d,
                    "velocity_per_day": velocity,
                    "days_of_stock":    days_of_stock,
                    "reorder_qty":      reorder_qty,
                    "flag":             flag,
                }
            )

    logger.info("Metrics computed for %d variants", len(results))
    return results


def _assign_flag(available: int, days_of_stock: float, sold_30d: int) -> str:
    """
    Flag priority (highest first):
      Critical  → days_of_stock < CRITICAL_DAYS and has sales
      Low       → days_of_stock < LOW_DAYS
      Dead Stock→ days_of_stock > DEAD_STOCK_DAYS AND sold_30d == 0
      OK        → everything else
    """
    if days_of_stock != float("inf") and days_of_stock < CRITICAL_DAYS:
        return "Critical"
    if days_of_stock != float("inf") and days_of_stock < LOW_DAYS:
        return "Low"
    if days_of_stock == float("inf") and available > 0 and sold_30d == 0:
        return "Dead Stock"
    if days_of_stock > DEAD_STOCK_DAYS and sold_30d == 0:
        return "Dead Stock"
    return "OK"
