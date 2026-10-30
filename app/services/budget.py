"""Byudjet matematikasi (sof funksiyalar, DB'siz).

Budget davri foydalanuvchi belgilagan [start, end] sanalar oralig'i (kalendar oy emas).
Davr summasi o'zgarmaydi. Kunlik limit har kuni qolgan summadan qayta hisoblanadi:

    bugungi limit = (davr boshidan beri qolgan + bugun sarflangan) / qolgan kunlar (bugun bilan)

Ko'p sarflasangiz keyingi kunlar limiti kamayadi, kam sarflasangiz ko'payadi.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class BudgetStatus:
    limit: int  # oylik limit
    spent: int  # oy boshidan sarflangan
    spent_today: int
    remaining: int  # oylik qolgan (manfiy bo'lishi mumkin)
    days_left: int  # bugun bilan
    daily_limit: int  # bugungi maksimum (kun boshidagi holatga ko'ra)
    today_left: int  # bugun yana qancha sarflash mumkin (manfiy = oshib ketgan)
    avg_daily: int  # o'tgan kunlardagi o'rtacha (bugun bilan)
    tomorrow_limit: int  # hozirgi holatda ertangi limit


def anchor_date(year: int, month: int, anchor: int) -> date:
    """`anchor`-kun shu oyda (oy qisqa bo'lsa oxirgi kunga tushiriladi). month 13 = keyingi yil yanvari."""
    year, month = year + (month - 1) // 12, (month - 1) % 12 + 1
    return date(year, month, min(anchor, calendar.monthrange(year, month)[1]))


def next_period(end: date, anchor: int) -> tuple[date, date]:
    """Tugagan davrdan keyingi davr: har oy `anchor`-kundan boshlanadi."""
    start = end + timedelta(days=1)
    boundary = anchor_date(start.year, start.month, anchor)
    if boundary <= start:
        boundary = anchor_date(start.year, start.month + 1, anchor)
    return start, boundary - timedelta(days=1)


def compute_status(
    limit: int, spent: int, spent_today: int, today: date, start: date, end: date
) -> BudgetStatus:
    # davr boshlanmagan bo'lsa birinchi kun, tugagan bo'lsa oxirgi kun deb olinadi
    eff = min(max(today, start), end)
    days_left = (end - eff).days + 1
    elapsed = (eff - start).days + 1
    remaining = limit - spent
    daily_limit = max(0, (remaining + spent_today) // days_left)
    next_days = days_left - 1
    tomorrow = max(0, remaining // next_days) if next_days > 0 else 0
    return BudgetStatus(
        limit=limit,
        spent=spent,
        spent_today=spent_today,
        remaining=remaining,
        days_left=days_left,
        daily_limit=daily_limit,
        today_left=daily_limit - spent_today,
        avg_daily=spent // elapsed,
        tomorrow_limit=tomorrow,
    )


def fmt_money(amount: int, currency: str = "so'm") -> str:
    return f"{amount:,}".replace(",", " ") + f" {currency}"
