"""
Daily briefing generator.
Produces a human-readable summary of inventory health.
Output goes to console (logger) and optionally to a .txt file.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from config.settings import REPORTS_DIR
from metrics.flags import get_low_stock, get_dead_stock, get_reorder_list

logger = logging.getLogger(__name__)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fmt_days(days) -> str:
    if days == float("inf"):
        return "∞"
    return f"{days:.1f}"


def build_briefing(metrics: list[dict]) -> str:
    """Build the full briefing text and return it as a string."""
    low  = get_low_stock(metrics)
    dead = get_dead_stock(metrics)
    reorder = get_reorder_list(metrics)

    critical = [r for r in low if r["flag"] == "Critical"]
    low_only = [r for r in low if r["flag"] == "Low"]

    lines = [
        "=" * 60,
        f"  INVENTORY BRIEFING — {_today()}",
        "=" * 60,
    ]

    # ── Critical ──────────────────────────────────────────────
    if critical:
        lines.append(f"\nCRITICAL ({len(critical)} SKUs — < 7 days stock):")
        for r in critical:
            lines.append(
                f"  {r['sku'] or r['variant_id']:<20} | {r['product_title'][:25]:<25} "
                f"| {r['total_available']:>5} units "
                f"| {_fmt_days(r['days_of_stock'])} days left "
                f"→ Reorder {r['reorder_qty']} units"
            )
    else:
        lines.append("\nCRITICAL: None")

    # ── Low ───────────────────────────────────────────────────
    if low_only:
        lines.append(f"\nLOW STOCK ({len(low_only)} SKUs — 7–14 days):")
        for r in low_only:
            lines.append(
                f"  {r['sku'] or r['variant_id']:<20} | {r['product_title'][:25]:<25} "
                f"| {r['total_available']:>5} units "
                f"| {_fmt_days(r['days_of_stock'])} days left "
                f"→ Reorder {r['reorder_qty']} units"
            )
    else:
        lines.append("\nLOW STOCK: None")

    # ── Dead Stock ────────────────────────────────────────────
    if dead:
        lines.append(f"\nDEAD STOCK ({len(dead)} SKUs — no sales, high inventory):")
        for r in dead[:5]:   # cap at 5 in briefing
            lines.append(
                f"  {r['sku'] or r['variant_id']:<20} | {r['product_title'][:25]:<25} "
                f"| {r['total_available']:>5} units | 0 sold/30d → Consider markdown"
            )
        if len(dead) > 5:
            lines.append(f"  ... and {len(dead) - 5} more (see dead_stock report)")
    else:
        lines.append("\nDEAD STOCK: None")

    # ── Summary ───────────────────────────────────────────────
    lines += [
        "",
        "-" * 60,
        f"REORDER SUMMARY: {len(reorder)} SKUs need action "
        f"({len(critical)} critical, {len(low_only)} low)",
        f"Full reports: reports/output/",
        "=" * 60,
    ]

    return "\n".join(lines)


def print_briefing(metrics: list[dict]):
    """Print briefing to stdout and logger."""
    text = build_briefing(metrics)
    print(text)
    logger.info("Daily briefing generated.")
    return text


def save_briefing(metrics: list[dict]) -> Path:
    """Save briefing to a dated .txt file."""
    text = build_briefing(metrics)
    out_dir = Path(REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"briefing_{_today()}.txt"
    path.write_text(text, encoding="utf-8")
    logger.info("Briefing saved to %s", path)
    return path
