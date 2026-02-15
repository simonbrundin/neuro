#!/usr/bin/env python3
import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime

from config import config, STATE_FILE
from scraper import fetch_portfolio
from notifier import send_notification


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(data: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_portfolio_changes(current_data: dict, previous_data: dict) -> dict:
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
    removed = list(prev_dict.keys())

    for row in current_portfolio[1:]:
        if not row or not row[0]:
            continue

        stock_name = row[0]
        current_weight = row[2] if len(row) > 2 else ""
        current_stocks.add(stock_name)

        if stock_name in removed:
            removed.remove(stock_name)

        if stock_name in prev_dict:
            prev_row = prev_dict[stock_name]
            prev_weight = prev_row[2] if len(prev_row) > 2 else ""

            try:
                curr_pct = float(current_weight.replace("%", "").replace(",", "."))
                prev_pct = float(prev_weight.replace("%", "").replace(",", "."))

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
            added.append(
                {
                    "name": stock_name,
                    "new_weight": current_weight,
                }
            )

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


def is_new_data(current_data: dict, previous_data: dict) -> bool:
    if not previous_data:
        return True

    current_date = current_data.get("date", "")
    previous_date = previous_data.get("date", "")

    if current_date != previous_date:
        return True

    return has_actual_changes(current_data, previous_data)


def main():
    print(f"[{datetime.now().isoformat()}] Checking NeuroQuant...")

    portfolio_data = asyncio.run(fetch_portfolio())

    if not portfolio_data:
        print("Failed to fetch portfolio data")
        sys.exit(1)

    portfolio_date = portfolio_data.get("date")
    print(f"Fetched data: date={portfolio_date}")

    if not portfolio_date:
        print("No valid date in portfolio data, skipping")
        sys.exit(1)

    previous_state = load_state()

    if is_new_data(portfolio_data, previous_state):
        print("New data detected! Sending notification...")

        changes = get_portfolio_changes(portfolio_data, previous_state)

        if send_notification(portfolio_data, changes):
            print("Notification sent successfully")
            save_state(portfolio_data)
        else:
            print("Failed to send notification")
            sys.exit(1)
    else:
        print("No new data")
        save_state(portfolio_data)


if __name__ == "__main__":
    main()
