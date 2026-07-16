from datetime import date

from backend.stats.service import StatsService


def test_rate_zero_denominator():
    assert StatsService.rate(3, 0) == 0.0


def test_rate():
    assert StatsService.rate(3, 4) == 75.0


def test_resolve_period_default_90_days():
    period, start_at, end_at = StatsService.resolve_period(
        date(2026, 1, 1),
        date(2026, 3, 31),
    )
    assert period.from_date == date(2026, 1, 1)
    assert period.to_date == date(2026, 3, 31)
    assert start_at.date() == date(2026, 1, 1)
    assert end_at.date() == date(2026, 4, 1)
