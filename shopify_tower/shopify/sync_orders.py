"""
Sync orders and line items from Shopify into SQLite.
"""
import logging
from datetime import datetime, timezone

from shopify.client import ShopifyClient
from db.database import db_conn

logger = logging.getLogger(__name__)


def _clean_price(value) -> float:
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _parse_dt(value: str) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Upsert helpers ────────────────────────────────────────────────────────────

def _upsert_order(conn, order: dict):
    conn.execute(
        """INSERT INTO orders
               (id, order_number, created_at, financial_status, total_price, synced_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
               financial_status=excluded.financial_status,
               total_price=excluded.total_price,
               synced_at=excluded.synced_at""",
        (
            str(order["id"]),
            str(order.get("order_number", "")),
            _parse_dt(order.get("created_at")),
            order.get("financial_status", ""),
            _clean_price(order.get("total_price", 0)),
            _now(),
        ),
    )


def _upsert_order_item(conn, item: dict, order_id: str, order_created_at: str):
    conn.execute(
        """INSERT INTO order_items
               (id, order_id, variant_id, sku, title, quantity, price, created_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
               quantity=excluded.quantity,
               price=excluded.price""",
        (
            str(item["id"]),
            order_id,
            str(item["variant_id"]) if item.get("variant_id") else None,
            item.get("sku") or "",
            item.get("title", ""),
            int(item.get("quantity") or 0),
            _clean_price(item.get("price", 0)),
            order_created_at,
        ),
    )


# ── Public sync function ──────────────────────────────────────────────────────

def sync_orders(client: ShopifyClient, created_at_min: str = None) -> int:
    """
    Pull all orders (status=any) from Shopify and upsert into DB.
    Pass created_at_min (ISO string) for incremental sync.
    Returns count of orders synced.
    """
    params = {}
    if created_at_min:
        params["created_at_min"] = created_at_min

    total_orders = 0
    total_items = 0

    for page in client.get_orders(params=params):
        with db_conn() as conn:
            for order in page:
                order_id = str(order["id"])
                order_created_at = _parse_dt(order.get("created_at"))
                _upsert_order(conn, order)
                total_orders += 1

                for item in order.get("line_items", []):
                    _upsert_order_item(conn, item, order_id, order_created_at)
                    total_items += 1

        logger.info("Orders sync: %d orders, %d line items so far",
                    total_orders, total_items)

    logger.info("Orders sync complete. Orders: %d | Line items: %d",
                total_orders, total_items)
    return total_orders
