from datetime import date

from app.services.budget import compute_status, fmt_money, next_period

OCT = (date(2026, 10, 1), date(2026, 10, 31))


def test_days_left_includes_today_and_last_day():
    assert compute_status(100, 0, 0, date(2026, 10, 1), *OCT).days_left == 31
    assert compute_status(100, 0, 0, date(2026, 10, 31), *OCT).days_left == 1


def test_even_split_at_month_start():
    s = compute_status(3_100_000, 0, 0, date(2026, 10, 1), *OCT)
    assert s.daily_limit == 100_000
    assert s.today_left == 100_000


def test_daily_limit_stable_during_the_day():
    before = compute_status(3_100_000, 0, 0, date(2026, 10, 1), *OCT)
    after = compute_status(3_100_000, 40_000, 40_000, date(2026, 10, 1), *OCT)
    assert before.daily_limit == after.daily_limit == 100_000
    assert after.today_left == 60_000


def test_overspending_lowers_next_days():
    # 1-kuni 200k sarflandi (limit 100k edi)
    s = compute_status(3_100_000, 200_000, 200_000, date(2026, 10, 1), *OCT)
    assert s.today_left == -100_000
    assert s.tomorrow_limit == 2_900_000 // 30
    assert s.tomorrow_limit < 100_000


def test_underspending_raises_next_days():
    s = compute_status(3_100_000, 20_000, 20_000, date(2026, 10, 1), *OCT)
    assert s.tomorrow_limit > 100_000


def test_monthly_total_is_conserved():
    # har kuni limitni to'liq sarflasak, oy oxirida budget aynan tugaydi
    limit, spent = 3_100_000, 0
    for d in range(1, 32):
        day = date(2026, 10, d)
        spend = compute_status(limit, spent, 0, day, *OCT).daily_limit
        spent += spend
    assert 0 <= limit - spent < 31


def test_budget_exhausted():
    s = compute_status(1_000_000, 1_200_000, 100_000, date(2026, 10, 10), *OCT)
    assert s.daily_limit == 0
    assert s.tomorrow_limit == 0
    assert s.remaining == -200_000


def test_fmt_money():
    assert fmt_money(1_250_000) == "1 250 000 so'm"


def test_custom_period_crossing_month_boundary():
    # 30-oktabrda boshlangan davr: 30.10 - 29.11 (31 kun)
    period = (date(2026, 10, 30), date(2026, 11, 29))
    s = compute_status(3_100_000, 0, 0, date(2026, 10, 30), *period)
    assert s.days_left == 31
    assert s.daily_limit == 100_000


def test_one_day_left_gets_whole_remainder():
    s = compute_status(500_000, 100_000, 0, date(2026, 10, 31), *OCT)
    assert s.days_left == 1
    assert s.daily_limit == 400_000
    assert s.tomorrow_limit == 0


def test_period_not_started_counts_from_first_day():
    s = compute_status(3_100_000, 0, 0, date(2026, 10, 25), date(2026, 11, 1), date(2026, 11, 30))
    assert s.days_left == 30
    assert s.avg_daily == 0


def test_next_period_follows_anchor_day():
    # 30-kundan boshlangan davr tugagach keyingisi 30-kundan
    assert next_period(date(2026, 11, 29), 30) == (date(2026, 11, 30), date(2026, 12, 29))
    # fevralda 30-kun yo'q: 28-fevralgacha qisqaradi, keyin yana 30-kunga qaytadi
    assert next_period(date(2027, 1, 29), 30) == (date(2027, 1, 30), date(2027, 2, 27))
    assert next_period(date(2027, 2, 27), 30) == (date(2027, 2, 28), date(2027, 3, 29))
    # yil almashishi
    assert next_period(date(2026, 12, 4), 5) == (date(2026, 12, 5), date(2027, 1, 4))


def test_next_period_from_irregular_first_period():
    # birinchi davr 30.10 - 15.11 qisqa bo'lsa, keyingisi 16.11 dan 29.11 gacha
    assert next_period(date(2026, 11, 15), 30) == (date(2026, 11, 16), date(2026, 11, 29))
