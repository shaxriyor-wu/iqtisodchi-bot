from app.bot.middlewares.ratelimit import SlidingWindow


def test_allows_five_per_second_then_blocks():
    w = SlidingWindow(5, 1.0)
    assert [w.allow(1, now=0.0 + i * 0.1) for i in range(6)] == [True] * 5 + [False]


def test_window_slides():
    w = SlidingWindow(5, 1.0)
    for i in range(5):
        assert w.allow(1, now=i * 0.1)
    assert not w.allow(1, now=0.9)
    assert w.allow(1, now=1.05)  # birinchi hodisa oynadan chiqdi


def test_users_are_independent():
    w = SlidingWindow(1, 1.0)
    assert w.allow(1, now=0)
    assert not w.allow(1, now=0.1)
    assert w.allow(2, now=0.1)
