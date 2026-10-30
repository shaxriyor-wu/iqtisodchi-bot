"""Statistika matnlari (AI'siz, token sarflamaydi)."""

from app.services.budget import fmt_money as m
from app.services.ledger import Overview

NO_BUDGET = (
    "Budget hali o'rnatilmagan yoki davri tugagan.\n"
    "Masalan yozing: «2 mln budget, 1-noyabrdan 30-noyabrgacha»"
)


def _period(ov: Overview) -> str:
    return f"{ov.period_start:%d.%m.%Y} – {ov.period_end:%d.%m.%Y}"


def _no_budget(ov: Overview) -> bool:
    return not ov.total.limit or ov.ended


def today(ov: Overview) -> str:
    t = ov.total
    if _no_budget(ov):
        return NO_BUDGET
    head = "✅" if t.today_left >= 0 else "⚠️ Limitdan oshdi!"
    return (
        f"📅 Bugun {head}\n\n"
        f"Maksimum: {m(t.daily_limit)}\n"
        f"Sarflandi: {m(t.spent_today)}\n"
        f"Yana mumkin: {m(max(t.today_left, 0))}\n\n"
        f"Ertangi limit: {m(t.tomorrow_limit)}"
    )


def average(ov: Overview) -> str:
    t = ov.total
    if _no_budget(ov):
        return NO_BUDGET
    return (
        f"📈 O'rtacha kunlik xarajat: {m(t.avg_daily)}\n"
        f"Maksimum kunlik limit: {m(t.daily_limit)}\n"
        f"Davr bo'yicha jami: {m(t.spent)}"
    )


def max_daily(ov: Overview) -> str:
    t = ov.total
    if _no_budget(ov):
        return NO_BUDGET
    return (
        f"🔝 Bugungi maksimum kunlik xarajat: {m(t.daily_limit)}\n"
        f"Ertaga: {m(t.tomorrow_limit)}\n\n"
        f"Qolgan {t.days_left} kun bo'yicha hisoblanadi."
    )


def month(ov: Overview) -> str:
    t = ov.total
    if _no_budget(ov):
        return NO_BUDGET
    pct = min(100, round(t.spent * 100 / t.limit))
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    return (
        f"💰 Budget: {m(t.limit)}\nDavr: {_period(ov)}\n"
        f"Sarflandi: {m(t.spent)} ({pct}%)\n[{bar}]\n"
        f"Qolgan: {m(t.remaining)}\n"
        f"Qolgan kunlar: {t.days_left}"
    )


def categories(ov: Overview) -> str:
    lines = ["🗂 Bo'limlar bo'yicha (joriy davr)\n"]
    for c in ov.categories:
        if c.status:
            s = c.status
            mark = "⚠️" if s.remaining < 0 else "•"
            lines.append(
                f"{mark} {c.name}: {m(c.spent)} / {m(s.limit)}\n"
                f"    qolgan {m(s.remaining)}, bugun yana {m(max(s.today_left, 0))}"
            )
        else:
            lines.append(f"• {c.name}: {m(c.spent)} (limitsiz)")
    return "\n".join(lines)


def recent(rows) -> str:
    if not rows:
        return "Hali xarajat yozilmagan."
    lines = ["🕘 Oxirgi xarajatlar\n"]
    for exp, cat in rows:
        note = f" — {exp.note}" if exp.note else ""
        lines.append(f"{exp.spent_at:%d.%m %H:%M}  {m(exp.amount)}  [{cat}]{note}")
    return "\n".join(lines)
