from datetime import datetime, timedelta

import pytest

from run_guard import RunGuard


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "runs.json"


def make_guard(state_file, now, **kwargs):
    options = {
        "max_runs_per_day": 100,
        "max_consecutive_failures": 3,
        "cooldown_minutes": 60,
        "locked_cooldown_minutes": 120,
        "now_provider": lambda: now,
    }
    options.update(kwargs)
    return RunGuard(state_file=state_file, **options)


def test_allows_run_and_counts_today(state_file):
    guard = make_guard(state_file, datetime(2026, 11, 2, 12, 0))
    allowed, reason = guard.start_run()

    assert allowed is True
    assert reason == ""
    assert guard.state.runs_today == 1


def test_blocks_after_daily_limit(state_file):
    guard = make_guard(state_file, datetime(2026, 11, 2, 12, 0), max_runs_per_day=2)

    assert guard.start_run()[0] is True
    assert guard.start_run()[0] is True
    allowed, reason = guard.start_run()

    assert allowed is False
    assert "daglig gräns" in reason


def test_count_resets_next_day(state_file):
    guard = make_guard(state_file, datetime(2026, 11, 2, 23, 50), max_runs_per_day=1)
    assert guard.start_run()[0] is True
    assert guard.start_run()[0] is False

    guard._now = lambda: datetime(2026, 11, 3, 0, 5)
    allowed, _ = guard.start_run()

    assert allowed is True
    assert guard.state.runs_today == 1


def test_pauses_after_consecutive_failures(state_file):
    now = datetime(2026, 11, 2, 12, 0)
    guard = make_guard(state_file, now, max_consecutive_failures=3)

    for _ in range(3):
        guard.record_failure()

    allowed, reason = guard.start_run()

    assert allowed is False
    assert "paus" in reason


def test_success_resets_failure_counter(state_file):
    guard = make_guard(state_file, datetime(2026, 11, 2, 12, 0))

    guard.record_failure()
    guard.record_failure()
    guard.record_success()

    assert guard.state.consecutive_failures == 0
    assert guard.start_run()[0] is True


def test_locked_account_uses_longer_cooldown(state_file):
    now = datetime(2026, 11, 2, 12, 0)
    guard = make_guard(state_file, now, max_consecutive_failures=3)

    guard.record_failure(locked=True)

    assert guard.start_run()[0] is False

    guard._now = lambda: now + timedelta(minutes=61)
    assert guard.start_run()[0] is False

    guard._now = lambda: now + timedelta(minutes=121)
    assert guard.start_run()[0] is True


def test_state_persists_between_guards(state_file):
    now = datetime(2026, 11, 2, 12, 0)
    guard = make_guard(state_file, now, max_runs_per_day=1)

    guard.start_run()

    next_guard = make_guard(state_file, now, max_runs_per_day=1)
    allowed, reason = next_guard.start_run()

    assert allowed is False
    assert "daglig gräns" in reason


def test_corrupt_state_file_does_not_crash(state_file):
    state_file.write_text("inte json")

    guard = make_guard(state_file, datetime(2026, 11, 2, 12, 0))

    assert guard.start_run()[0] is True
