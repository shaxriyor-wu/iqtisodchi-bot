"""Foydalanuvchi byudjeti, bo'limlar va xarajatlar bilan ishlash."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Category, Expense, User
from app.services.budget import BudgetStatus, compute_status, next_period

DEFAULT_CATEGORY = "Boshqa"
SEED_CATEGORIES = ["Transport", "Oziq-ovqat", "Cs2", "Snak", DEFAULT_CATEGORY]


class LedgerError(Exception):
    """Foydalanuvchiga ko'rsatish mumkin bo'lgan xato."""


@dataclass(frozen=True)
class CategoryStatus:
    name: str
    status: BudgetStatus | None  # limit qo'yilmagan bo'lsa None
    spent: int
    spent_today: int


@dataclass(frozen=True)
class Overview:
    total: BudgetStatus
    period_start: date | None
    period_end: date | None
    ended: bool  # davr tugagan va avto-takror o'chiq
    not_started: bool
    categories: list[CategoryStatus]


def _now() -> datetime:
    return datetime.now(get_settings().tz)


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def ensure_user(s: AsyncSession, user_id: int) -> User:
    user = await s.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        s.add(user)
        await s.flush()  # FK tartibi: avval users
        s.add_all(Category(user_id=user_id, name=n) for n in SEED_CATEGORIES)
        await s.commit()
    return user


async def register_phone(s: AsyncSession, user_id: int, phone: str) -> User:
    """Telefon raqamni Telegram ID bilan bog'laydi."""
    phone = "+" + phone.lstrip("+")
    owner = await s.scalar(select(User).where(User.phone == phone))
    if owner is not None and owner.id != user_id:
        raise LedgerError("Bu raqam boshqa akkauntga bog'langan.")
    user = await ensure_user(s, user_id)
    user.phone = phone
    await s.commit()
    return user


async def is_registered(s: AsyncSession, user_id: int) -> bool:
    user = await s.get(User, user_id)
    return user is not None and user.phone is not None


async def list_categories(s: AsyncSession, user_id: int) -> list[Category]:
    rows = await s.scalars(
        select(Category).where(Category.user_id == user_id).order_by(Category.id)
    )
    return list(rows)


async def _find_category(s: AsyncSession, user_id: int, name: str) -> Category | None:
    return await s.scalar(
        select(Category).where(
            Category.user_id == user_id, func.lower(Category.name) == name.strip().lower()
        )
    )


async def _check_limits_fit(
    s: AsyncSession, user_id: int, budget: int, extra: dict[int, int | None]
):
    """Bo'lim limitlari yig'indisi oylik budgetdan oshmasligi kerak."""
    cats = await list_categories(s, user_id)
    total = 0
    for c in cats:
        lim = extra.get(c.id, c.monthly_limit)
        total += lim or 0
    if total > budget:
        raise LedgerError(
            f"Bo'limlar limiti yig'indisi ({total:,}) oylik budgetdan ({budget:,}) oshib ketadi."
        )


MAX_PERIOD_DAYS = 93


async def set_budget(
    s: AsyncSession,
    user_id: int,
    amount: int,
    start: date | None = None,
    end: date | None = None,
    repeat: bool | None = None,
) -> User:
    """Budgetni davr bilan o'rnatadi. Sana berilmasa joriy davr saqlanadi."""
    if amount <= 0:
        raise LedgerError("Budget musbat son bo'lishi kerak.")
    user = await ensure_user(s, user_id)
    if start is None and end is None:
        cur = current_period(user, _now().date())
        if cur is None:
            raise LedgerError("Budget davri noma'lum: qachondan qachongacha amal qilishini ayting.")
        start, end = cur
    elif start is None or end is None:
        raise LedgerError("Davrning boshlanish va tugash sanasi ikkalasi ham kerak.")
    if end < start:
        raise LedgerError("Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas.")
    if (end - start).days + 1 > MAX_PERIOD_DAYS:
        raise LedgerError(f"Davr {MAX_PERIOD_DAYS} kundan uzun bo'lmasligi kerak.")
    if end < _now().date():
        raise LedgerError("Davr allaqachon tugagan: tugash sanasi o'tmishda.")
    await _check_limits_fit(s, user_id, amount, {})
    user.monthly_budget = amount
    user.period_start, user.period_end = start, end
    user.anchor_day = start.day
    if repeat is not None:
        user.auto_renew = repeat
    await s.commit()
    return user


def current_period(user: User, today: date) -> tuple[date, date] | None:
    """Foydalanuvchining hozirgi davri; belgilanmagan bo'lsa None."""
    if user.period_start and user.period_end:
        return user.period_start, user.period_end
    return None


def _roll_period(user: User, today: date) -> bool:
    """Davr tugagan va avto-takror yoqilgan bo'lsa, keyingi davrga o'tkazadi."""
    if not (user.period_end and user.auto_renew and user.anchor_day):
        return False
    rolled = False
    while today > user.period_end:
        user.period_start, user.period_end = next_period(user.period_end, user.anchor_day)
        rolled = True
    return rolled


async def set_category(
    s: AsyncSession, user_id: int, name: str, monthly_limit: int | None
) -> Category:
    name = name.strip()[:40]
    if not name:
        raise LedgerError("Bo'lim nomi bo'sh bo'lishi mumkin emas.")
    if monthly_limit is not None and monthly_limit < 0:
        raise LedgerError("Limit manfiy bo'lishi mumkin emas.")
    user = await ensure_user(s, user_id)
    cat = await _find_category(s, user_id, name)
    if cat is None:
        cat = Category(user_id=user_id, name=name.capitalize())
        s.add(cat)
        await s.flush()
    await _check_limits_fit(s, user_id, user.monthly_budget, {cat.id: monthly_limit})
    cat.monthly_limit = monthly_limit
    await s.commit()
    return cat


async def delete_category(s: AsyncSession, user_id: int, name: str) -> None:
    cat = await _find_category(s, user_id, name)
    if cat is None:
        raise LedgerError(f"'{name}' bo'limi topilmadi.")
    if cat.name == DEFAULT_CATEGORY:
        raise LedgerError(f"'{DEFAULT_CATEGORY}' bo'limini o'chirib bo'lmaydi.")
    default = await _find_category(s, user_id, DEFAULT_CATEGORY)
    await s.execute(
        Expense.__table__.update()
        .where(Expense.category_id == cat.id)
        .values(category_id=default.id)
    )
    await s.execute(delete(Category).where(Category.id == cat.id))
    await s.commit()


async def add_expense(
    s: AsyncSession,
    user_id: int,
    amount: int,
    category: str,
    note: str = "",
    on_date: date | None = None,
) -> Expense:
    if amount <= 0:
        raise LedgerError("Summa musbat bo'lishi kerak.")
    await ensure_user(s, user_id)
    cat = await _find_category(s, user_id, category or DEFAULT_CATEGORY)
    if cat is None:
        names = ", ".join(c.name for c in await list_categories(s, user_id))
        raise LedgerError(f"'{category}' bo'limi yo'q. Mavjud bo'limlar: {names}")
    exp = Expense(user_id=user_id, category_id=cat.id, amount=amount, note=note[:200])
    if on_date is not None:
        tz = get_settings().tz
        if on_date > _now().date():
            raise LedgerError("Kelajak sanasiga xarajat yozib bo'lmaydi.")
        exp.spent_at = datetime.combine(on_date, time(12, 0), tzinfo=tz)
    s.add(exp)
    await s.commit()
    return exp


async def delete_last_expense(s: AsyncSession, user_id: int) -> Expense:
    exp = await s.scalar(
        select(Expense).where(Expense.user_id == user_id).order_by(Expense.id.desc()).limit(1)
    )
    if exp is None:
        raise LedgerError("O'chiradigan xarajat yo'q.")
    await s.delete(exp)
    await s.commit()
    return exp


async def recent_expenses(s: AsyncSession, user_id: int, limit: int = 10):
    rows = await s.execute(
        select(Expense, Category.name)
        .join(Category, Category.id == Expense.category_id)
        .where(Expense.user_id == user_id)
        .order_by(Expense.id.desc())
        .limit(limit)
    )
    return rows.all()


MAX_HISTORY_DAYS = 366


async def history(s: AsyncSession, user_id: int, days: int):
    """Oxirgi `days` kun (bugun bilan) xarajatlari: [(Expense, bo'lim nomi)], eskisidan yangisiga."""
    if days < 1:
        raise LedgerError("Kunlar soni 1 dan kam bo'lmasligi kerak.")
    days = min(days, MAX_HISTORY_DAYS)
    since = _day_start(_now()) - timedelta(days=days - 1)
    rows = await s.execute(
        select(Expense, Category.name)
        .join(Category, Category.id == Expense.category_id)
        .where(Expense.user_id == user_id, Expense.spent_at >= since)
        .order_by(Expense.spent_at, Expense.id)
    )
    return rows.all()


async def get_overview(s: AsyncSession, user_id: int) -> Overview:
    user = await ensure_user(s, user_id)
    now = _now()
    today, day_start = now.date(), _day_start(now)
    if _roll_period(user, today):
        await s.commit()
    period = current_period(user, today)
    if period is None:
        # budget hali o'rnatilmagan: statistika bo'sh, davr yo'q
        start = end = today
        limit = 0
    else:
        (start, end), limit = period, user.monthly_budget
    ended, not_started = today > end, today < start
    tz = get_settings().tz
    since = datetime.combine(start, time.min, tzinfo=tz)
    until = datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz)

    rows = await s.execute(
        select(
            Expense.category_id,
            func.coalesce(func.sum(Expense.amount), 0),
            func.coalesce(func.sum(Expense.amount).filter(Expense.spent_at >= day_start), 0),
        )
        .where(Expense.user_id == user_id, Expense.spent_at >= since, Expense.spent_at < until)
        .group_by(Expense.category_id)
    )
    per_cat = {cid: (int(m), int(d)) for cid, m, d in rows}

    total_spent = sum(m for m, _ in per_cat.values())
    total_today = sum(d for _, d in per_cat.values())
    total = compute_status(limit, total_spent, total_today, today, start, end)

    cats = []
    for c in await list_categories(s, user_id):
        spent, spent_today = per_cat.get(c.id, (0, 0))
        st = (
            compute_status(c.monthly_limit, spent, spent_today, today, start, end)
            if c.monthly_limit and period
            else None
        )
        cats.append(CategoryStatus(c.name, st, spent, spent_today))
    return Overview(
        total, start if period else None, end if period else None, ended, not_started, cats
    )
