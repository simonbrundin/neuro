"""Skydd mot att överkörning låser NeuroQuant-kontot.

NeuroQuant låser ett konto efter 100 misslyckade inloggningsförsök. Den här
modulen håller koll på:

- antal körningar per dygn (daglig gräns)
- upprepade fel (avbryt och vänta en stund innan nästa försök)
- explicit kontolåsning (längre paus)

State sparas i runs.json (gitignoreras) så att gränserna överlever omstarter.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
RUN_STATE_FILE = BASE_DIR / "runs.json"


@dataclass
class RunState:
    date: str = ""
    runs_today: int = 0
    consecutive_failures: int = 0
    last_failure: str | None = None
    last_success: str | None = None
    locked: bool = False


class RunGuard:
    """Bestämmer om en körning får ske, och sparar resultatet av den."""

    def __init__(
        self,
        state_file: Path | str = RUN_STATE_FILE,
        max_runs_per_day: int = 96,
        max_consecutive_failures: int = 3,
        cooldown_minutes: int = 60,
        locked_cooldown_minutes: int = 120,
        now_provider=None,
    ):
        self.state_file = Path(state_file)
        self.max_runs_per_day = max_runs_per_day
        self.max_consecutive_failures = max_consecutive_failures
        self.cooldown_minutes = cooldown_minutes
        self.locked_cooldown_minutes = locked_cooldown_minutes
        self._now = now_provider or datetime.now
        self.state = self._load()

    def _load(self) -> RunState:
        if not self.state_file.exists():
            return RunState()
        try:
            data = json.loads(self.state_file.read_text())
        except (json.JSONDecodeError, OSError):
            return RunState()
        known = set(RunState.__dataclass_fields__)
        return RunState(**{k: v for k, v in data.items() if k in known})

    def _save(self) -> None:
        self.state_file.write_text(json.dumps(asdict(self.state), indent=2))

    def _roll_day(self, now: datetime) -> None:
        today = now.date().isoformat()
        if self.state.date != today:
            self.state.date = today
            self.state.runs_today = 0

    def cooldown_until(self, now: datetime | None = None) -> datetime | None:
        """Returnerar tidpunkt då nästa körning får ske, eller None.

        Pausens längd växer med antalet fel i rad, så att ett trasigt
        inloggning inte ger 24 försök per dygn.
        """
        if self.state.consecutive_failures < self.max_consecutive_failures:
            return None
        if not self.state.last_failure:
            return None
        try:
            last = datetime.fromisoformat(self.state.last_failure)
        except ValueError:
            return None
        if self.state.locked:
            minutes = self.locked_cooldown_minutes
        else:
            minutes = self.cooldown_minutes * self.state.consecutive_failures
        return last + timedelta(minutes=minutes)

    def start_run(self) -> tuple[bool, str]:
        """Reserverar en körning. Returnerar (tillåten, orsak)."""
        now = self._now()
        self._roll_day(now)
        self._save()

        if self.state.runs_today >= self.max_runs_per_day:
            return False, (
                f"daglig gräns nådd ({self.state.runs_today} körningar, "
                f"max {self.max_runs_per_day})"
            )

        until = self.cooldown_until(now)
        if until and now < until:
            return False, (
                f"paus efter {self.state.consecutive_failures} fel, "
                f"nästa försök tidigast {until:%Y-%m-%d %H:%M}"
            )

        self.state.runs_today += 1
        self._save()
        return True, ""

    def record_success(self) -> None:
        self.state.consecutive_failures = 0
        self.state.locked = False
        self.state.last_success = self._now().isoformat()
        self._save()

    def record_failure(self, locked: bool = False) -> None:
        self.state.consecutive_failures += 1
        self.state.last_failure = self._now().isoformat()
        if locked:
            # Ett låst konto måste återlåsas av administratör -> använd längre paus.
            self.state.locked = True
            self.state.consecutive_failures = max(
                self.state.consecutive_failures, self.max_consecutive_failures
            )
        self._save()

    def status(self) -> str:
        return (
            f"{self.state.runs_today}/{self.max_runs_per_day} körningar idag, "
            f"{self.state.consecutive_failures} fel i rad"
        )
