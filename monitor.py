#!/usr/bin/env python3
import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime

from config import config, STATE_FILE
from run_guard import RunGuard
from scraper import (
    fetch_portfolio,
    AccountLockedError,
    InvalidCredentialsError,
    VerificationCodeError,
)
from notifier import send_notification, send_email


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(data: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def parse_weight(weight) -> float | None:
    """Tolkar en vikt som '3.8%' till 3.8."""
    if weight is None:
        return None
    try:
        return float(str(weight).replace("%", "").replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def is_significant(weight, threshold: float) -> bool:
    """Sant om en viktändring är större än tröskeln.

    En post som tillkommit (vikt > 0) eller försvunnit (tidigare vikt > 0)
    räknas som en ändring på hela vikten.
    """
    value = parse_weight(weight)
    if value is None:
        # Okänd vikt - ta med hellre än att tappa en riktig ändring.
        return True
    return round(value, 6) > threshold


def is_new_publication(current_data: dict, previous_data: dict) -> bool:
    """Sant om NeuroQuant har publicerat en ny version av portföljen.

    Vikterna på sajten är volatilitetsjusterade och räknas om löpande,
    så en viktändring ensam betyder inte att portföljen publicerats om.
    Det är publiceringsdatumet (updatedAt) som avgör.
    """
    if not previous_data:
        return False

    if current_data.get("date", "") != previous_data.get("date", ""):
        return True

    current_version = current_data.get("updated_at")
    previous_version = previous_data.get("updated_at")
    if current_version and previous_version:
        return current_version != previous_version

    return False


def get_portfolio_changes(
    current_data: dict, previous_data: dict, threshold: float = None
) -> dict:
    if threshold is None:
        threshold = config.min_change_threshold

    current_portfolio = current_data.get("data", [])
    previous_portfolio = previous_data.get("data", [])

    if not previous_portfolio:
        return {"increased": [], "decreased": [], "added": [], "removed": []}

    prev_dict = {}
    for row in previous_portfolio[1:]:
        if row and row[0]:
            prev_dict[row[0]] = row

    current_stocks = set()
    increased = []
    decreased = []
    added = []
    removed = []

    for row in current_portfolio[1:]:
        if not row or not row[0]:
            continue

        stock_name = row[0]
        current_weight = row[2] if len(row) > 2 else ""
        current_stocks.add(stock_name)

        if stock_name in prev_dict:
            prev_row = prev_dict[stock_name]
            prev_weight = prev_row[2] if len(prev_row) > 2 else ""

            try:
                curr_pct = float(current_weight.replace("%", "").replace(",", "."))
                prev_pct = float(prev_weight.replace("%", "").replace(",", "."))

                change_pct = round(abs(curr_pct - prev_pct), 6)

                if change_pct <= threshold:
                    continue

                if curr_pct > prev_pct:
                    increased.append(
                        {
                            "name": stock_name,
                            "old_weight": prev_weight,
                            "new_weight": current_weight,
                        }
                    )
                elif curr_pct < prev_pct:
                    decreased.append(
                        {
                            "name": stock_name,
                            "old_weight": prev_weight,
                            "new_weight": current_weight,
                        }
                    )
            except (ValueError, AttributeError):
                pass
        else:
            if is_significant(current_weight, threshold):
                added.append(
                    {
                        "name": stock_name,
                        "new_weight": current_weight,
                    }
                )

    # Positioner som fanns tidigare men inte finns nu.
    for name, prev_row in prev_dict.items():
        if name in current_stocks:
            continue
        prev_weight = prev_row[2] if len(prev_row) > 2 else ""
        if is_significant(prev_weight, threshold):
            removed.append({"name": name, "old_weight": prev_weight})

    return {
        "increased": increased,
        "decreased": decreased,
        "added": added,
        "removed": removed,
    }


def has_actual_changes(current_data: dict, previous_data: dict) -> bool:
    if not previous_data:
        return True

    changes = get_portfolio_changes(current_data, previous_data)

    return bool(
        changes["increased"]
        or changes["decreased"]
        or changes["added"]
        or changes["removed"]
    )


def main():
    guard = RunGuard(
        max_runs_per_day=config.max_runs_per_day,
        max_consecutive_failures=config.max_consecutive_failures,
        cooldown_minutes=config.failure_cooldown_minutes,
        locked_cooldown_minutes=config.locked_cooldown_minutes,
    )

    if "--reset" in sys.argv:
        guard.reset()
        print("Run guard state reset")
        sys.exit(0)

    allowed, reason = guard.start_run()
    if not allowed:
        print(f"[{datetime.now().isoformat()}] Skipping run: {reason}")
        sys.exit(0)

    print(f"[{datetime.now().isoformat()}] Checking NeuroQuant...")

    try:
        portfolio_data = asyncio.run(fetch_portfolio())
    except AccountLockedError as e:
        print(f"Account locked: {e}")
        guard.record_failure(locked=True)
        if guard.should_alert():
            send_email(
                "NeuroQuant: kontot är låst",
                "Hej!\n\n"
                "NeuroQuant-monitorn upptäckte att kontot är låst av NeuroQuant.\n"
                f"Detaljer: {e}\n\n"
                "Inga fler inloggningsförsök görs förrän pausen gått ut.\n\n"
                "---\nNeuroQuant Monitor",
            )
        sys.exit(0)
    except InvalidCredentialsError as e:
        print(f"Invalid credentials: {e}")
        guard.record_failure(
            locked=True,
            pause_minutes=config.invalid_credentials_cooldown_minutes,
        )
        if guard.should_alert():
            send_email(
                "NeuroQuant: inloggningen misslyckades",
                "Hej!\n\n"
                "NeuroQuant-monitorn kunde inte logga in - lösenordet verkar vara fel.\n"
                f"Detaljer: {e}\n\n"
                "Inga nya inloggningsförsök görs inom "
                f"{config.invalid_credentials_cooldown_minutes // 60} timmar.\n"
                "Uppdatera NEURO_PASSWORD i .env på pxe-servern.\n\n"
                "---\nNeuroQuant Monitor",
            )
        sys.exit(0)

    except VerificationCodeError as e:
        print(f"Verification code error: {e}")
        guard.record_failure()
        if guard.should_alert():
            send_email(
                "NeuroQuant: kunde inte hämta verifieringskoden",
                "Hej!\n\n"
                "NeuroQuant-monitorn kunde inte hämta verifieringskoden från inkorgen.\n"
                f"Detaljer: {e}\n\n"
                "Kontrollera att NeuroQuant-kontot och inkorgen är samma konto.\n\n"
                "---\nNeuroQuant Monitor",
            )
        sys.exit(1)

    if not portfolio_data:
        print("Failed to fetch portfolio data")
        guard.record_failure()
        sys.exit(1)

    portfolio_date = portfolio_data.get("date")
    print(f"Fetched data: date={portfolio_date}")

    guard.record_success()

    if not portfolio_date:
        print("No valid date in portfolio data, skipping")
        sys.exit(1)

    previous_state = load_state()

    if not previous_state:
        print("Ingen utgångsläge - sparar aktuell portfölj som baslinje")
        save_state(portfolio_data)
        return

    if not is_new_publication(portfolio_data, previous_state):
        print("Ingen ny publicering - inget att rapportera")
        return

    changes = get_portfolio_changes(portfolio_data, previous_state)
    save_state(portfolio_data)

    if not any(changes.values()):
        print(
            f"Inga förändringar över tröskeln "
            f"({config.min_change_threshold} procentenheter) - inget mejl"
        )
        return

    print("Ny publicering med förändringar - skickar mejl...")

    if send_notification(portfolio_data, changes):
        print("Notification sent successfully")
    else:
        print("Failed to send notification")
        sys.exit(1)


if __name__ == "__main__":
    main()
