from datetime import UTC, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.ai.tools import history_dict
from app.services.export import build_csv

TZ = ZoneInfo("Asia/Tashkent")


def _row(day, amount, cat, note=""):
    return SimpleNamespace(
        spent_at=datetime(2026, 10, day, 8, 30, tzinfo=UTC), amount=amount, note=note
    ), cat


ROWS = [_row(1, 15_000, "Transport", "taksi"), _row(1, 30_000, "Snak"), _row(2, 50_000, "Cs2")]


def test_csv_has_bom_header_and_local_time():
    data = build_csv(ROWS, TZ)
    assert data.startswith(b"\xef\xbb\xbf")
    lines = data.decode("utf-8-sig").splitlines()
    assert lines[0] == "Sana,Vaqt,Bo'lim,Summa (so'm),Izoh"
    assert lines[1] == "2026-10-01,13:30,Transport,15000,taksi"  # UTC+5


def test_csv_neutralises_formulas():
    row = _row(1, 1, "Boshqa", "=HYPERLINK(1)")
    assert "'=HYPERLINK(1)" in build_csv([row], TZ).decode("utf-8-sig")


def test_history_dict_totals():
    d = history_dict(ROWS, TZ)
    assert d["total"] == 95_000
    assert d["by_category"]["Cs2"] == 50_000
    assert d["by_day"] == {"2026-10-01": 45_000, "2026-10-02": 50_000}
    assert d["count"] == 3
