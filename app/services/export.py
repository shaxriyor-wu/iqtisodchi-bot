import csv
import io
from zoneinfo import ZoneInfo

_FORMULA_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _safe(text: str) -> str:
    """Excel/Sheets'da izoh formula sifatida ishlab ketmasligi uchun."""
    return "'" + text if text.startswith(_FORMULA_CHARS) else text


def build_csv(rows, tz: ZoneInfo) -> bytes:
    """rows: (Expense, bo'lim nomi) juftliklari. UTF-8 BOM bilan: Excel kirillcha/o'zbekchani to'g'ri ochadi."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Sana", "Vaqt", "Bo'lim", "Summa (so'm)", "Izoh"])
    for exp, cat in rows:
        local = exp.spent_at.astimezone(tz)
        w.writerow([f"{local:%Y-%m-%d}", f"{local:%H:%M}", _safe(cat), exp.amount, _safe(exp.note)])
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")
