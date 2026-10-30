"""Claude'ga beriladigan asboblar va ularning bajarilishi."""

import dataclasses
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services import ledger
from app.services.export import build_csv


@dataclass
class Outbox:
    """Asbob yaratgan, foydalanuvchiga yuboriladigan fayllar: (nom, bytes)."""

    files: list[tuple[str, bytes]] = field(default_factory=list)


TOOLS = [
    {
        "name": "add_expense",
        "description": "Xarajat yozadi. Summa so'mda, butun son (120 ming = 120000, 2 mln = 2000000).",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "so'mda"},
                "category": {"type": "string", "description": "mavjud bo'lim nomi"},
                "note": {"type": "string", "description": "nima uchun, qisqa"},
                "date": {
                    "type": "string",
                    "description": "YYYY-MM-DD, faqat bugun bo'lmasa (masalan 'kecha')",
                },
            },
            "required": ["amount", "category"],
        },
    },
    {
        "name": "delete_last_expense",
        "description": "Oxirgi yozilgan xarajatni o'chiradi (xatoni tuzatish uchun).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_budget",
        "description": (
            "Budgetni davr bilan o'rnatadi: summa va davr sanalari (qachondan qachongacha). "
            "Sanalarni foydalanuvchi aytmagan bo'lsa chaqirma, avval so'ra. Faqat summani "
            "o'zgartirish uchun sanalarni qoldirish mumkin (joriy davr saqlanadi)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "davr uchun jami, so'mda"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD, birinchi kun"},
                "end_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD, oxirgi kun (shu kun ham kiradi)",
                },
                "repeat_monthly": {
                    "type": "boolean",
                    "description": "davr tugagach shu kundan boshlab har oy avtomatik takrorlansinmi (default true)",
                },
            },
            "required": ["amount"],
        },
    },
    {
        "name": "set_category",
        "description": (
            "Bo'lim yaratadi yoki oylik limitini o'zgartiradi. "
            "monthly_limit berilmasa bo'limga alohida limit qo'yilmaydi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "monthly_limit": {"type": "integer"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "delete_category",
        "description": "Bo'limni o'chiradi; xarajatlari 'Boshqa' ga o'tadi.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_history",
        "description": (
            "Oxirgi N kunlik xarajatlar tarixi: jami, bo'limlar bo'yicha va kunlar bo'yicha "
            "yig'indi, oxirgi xarajatlar ro'yxati. 'Nimalarga ketdi' savollari uchun."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "1..366"}},
            "required": ["days"],
        },
    },
    {
        "name": "export_csv",
        "description": (
            "Oxirgi N kunlik xarajatlarni CSV fayl qilib foydalanuvchiga yuboradi. "
            "Foydalanuvchi fayl/CSV/jadval so'raganda chaqir."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "1..366"}},
            "required": ["days"],
        },
    },
    {
        "name": "get_overview",
        "description": (
            "Joriy holat: budget davri (sanalari), budget, sarflangan, qolgan, bugungi va ertangi limit, "
            "o'rtacha kunlik xarajat, bo'limlar bo'yicha holat."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


def overview_dict(ov: ledger.Overview) -> dict:
    return {
        "period": {
            "start": ov.period_start.isoformat() if ov.period_start else None,
            "end": ov.period_end.isoformat() if ov.period_end else None,
            "ended": ov.ended,
            "not_started": ov.not_started,
        },
        "total": dataclasses.asdict(ov.total),
        "categories": [
            {
                "name": c.name,
                "spent": c.spent,
                "spent_today": c.spent_today,
                "status": dataclasses.asdict(c.status) if c.status else None,
            }
            for c in ov.categories
        ],
    }


def history_dict(rows, tz, limit: int = 40) -> dict:
    by_cat: dict[str, int] = defaultdict(int)
    by_day: dict[str, int] = defaultdict(int)
    for exp, cat in rows:
        by_cat[cat] += exp.amount
        by_day[f"{exp.spent_at.astimezone(tz):%Y-%m-%d}"] += exp.amount
    return {
        "count": len(rows),
        "total": sum(by_cat.values()),
        "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1])),
        "by_day": dict(sorted(by_day.items())),
        "latest": [
            {
                "date": f"{e.spent_at.astimezone(tz):%Y-%m-%d}",
                "amount": e.amount,
                "category": c,
                "note": e.note,
            }
            for e, c in rows[-limit:]
        ],
    }


async def run_tool(
    s: AsyncSession, user_id: int, name: str, args: dict, outbox: Outbox
) -> tuple[str, bool]:
    """(natija matni, xatomi) qaytaradi."""
    try:
        match name:
            case "add_expense":
                on_date = date.fromisoformat(args["date"]) if args.get("date") else None
                await ledger.add_expense(
                    s, user_id, int(args["amount"]), args["category"], args.get("note", ""), on_date
                )
            case "delete_last_expense":
                exp = await ledger.delete_last_expense(s, user_id)
                return json.dumps({"deleted_amount": exp.amount}), False
            case "set_budget":
                await ledger.set_budget(
                    s,
                    user_id,
                    int(args["amount"]),
                    date.fromisoformat(args["start_date"]) if args.get("start_date") else None,
                    date.fromisoformat(args["end_date"]) if args.get("end_date") else None,
                    args.get("repeat_monthly"),
                )
            case "set_category":
                limit = args.get("monthly_limit")
                await ledger.set_category(
                    s, user_id, args["name"], int(limit) if limit is not None else None
                )
            case "delete_category":
                await ledger.delete_category(s, user_id, args["name"])
            case "get_history":
                rows = await ledger.history(s, user_id, int(args["days"]))
                return json.dumps(history_dict(rows, get_settings().tz), ensure_ascii=False), False
            case "export_csv":
                days = int(args["days"])
                rows = await ledger.history(s, user_id, days)
                if not rows:
                    return "Bu davrda xarajat yo'q, fayl yaratilmadi.", True
                outbox.files.append(
                    (f"xarajatlar_{days}_kun.csv", build_csv(rows, get_settings().tz))
                )
                return json.dumps({"ok": True, "rows": len(rows), "note": "fayl yuboriladi"}), False
            case "get_overview":
                pass
            case _:
                return f"Noma'lum asbob: {name}", True
        ov = await ledger.get_overview(s, user_id)
        return json.dumps({"ok": True, **overview_dict(ov)}, ensure_ascii=False), False
    except ledger.LedgerError as e:
        await s.rollback()
        return str(e), True
    except (KeyError, ValueError, TypeError) as e:
        await s.rollback()
        return f"Noto'g'ri argument: {e}", True
