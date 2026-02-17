"""
Step definitions for threshold BDD tests with behave.

These step definitions implement the tests from threshold.feature
to verify the MIN_CHANGE_THRESHOLD functionality.
"""

import sys
from pathlib import Path
from unittest.mock import patch

from behave import given, when, then

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from monitor import get_portfolio_changes
from config import Config


# ============================================================================
# GIVEN STEPS - Setup
# ============================================================================


@given("the config has MIN_CHANGE_THRESHOLD available")
def step_config_available(context):
    """The config has MIN_CHANGE_THRESHOLD available."""
    # This is true - config already has all env vars
    pass


@given("the previous portfolio had {stock} at {weight}")
def step_previous_portfolio_single(context, stock, weight):
    """The previous portfolio had a stock at a specific weight."""
    # Strip quotes from Gherkin parameters
    stock = stock.strip('"').strip("'")
    weight = weight.strip('"').strip("'")

    if not hasattr(context, "previous_data"):
        context.previous_data = {
            "date": "2026-01-01",
            "data": [
                ["Stock", "Action", "Vikt", "Kurs"],
                [stock, "Köp", weight, "100.00"],
            ],
        }
    else:
        # Add to existing data
        context.previous_data["data"].append([stock, "Köp", weight, "100.00"])


@given("the current portfolio has {stock} at {weight}")
def step_current_portfolio_single(context, stock, weight):
    """The current portfolio has a stock at a specific weight."""
    # Strip quotes from Gherkin parameters
    stock = stock.strip('"').strip("'")
    weight = weight.strip('"').strip("'")

    if not hasattr(context, "current_data"):
        context.current_data = {
            "date": "2026-02-01",
            "data": [
                ["Stock", "Action", "Vikt", "Kurs"],
                [stock, "Köp", weight, "100.00"],
            ],
        }
    else:
        # Add to existing data
        context.current_data["data"].append([stock, "Köp", weight, "100.00"])


@given("the previous portfolio had:")
def step_previous_portfolio_table(context):
    """The previous portfolio had a table of stocks."""
    table = context.table
    context.previous_data = {
        "date": "2026-01-01",
        "data": [["Stock", "Action", "Vikt", "Kurs"]],
    }
    for row in table:
        context.previous_data["data"].append(
            [row["stock"], "Köp", row["weight"], "100.00"]
        )


@given("the current portfolio has:")
def step_current_portfolio_table(context):
    """The current portfolio has a table of stocks."""
    table = context.table
    context.current_data = {
        "date": "2026-02-01",
        "data": [["Stock", "Action", "Vikt", "Kurs"]],
    }
    for row in table:
        context.current_data["data"].append(
            [row["stock"], "Köp", row["weight"], "100.00"]
        )


@given("MIN_CHANGE_THRESHOLD is set to {value}")
def step_set_threshold(context, value):
    """MIN_CHANGE_THRESHOLD is set to a specific value."""
    value = value.strip('"').strip("'")
    try:
        parsed = float(value)
        context.threshold_value = max(0.0, parsed)
    except (ValueError, TypeError):
        context.threshold_value = 0.0

    with patch.dict("os.environ", {"MIN_CHANGE_THRESHOLD": value}):
        import importlib
        import config as config_module

        importlib.reload(config_module)
        context.threshold_config = config_module.Config()


@given("MIN_CHANGE_THRESHOLD is not set")
def step_unset_threshold(context):
    """MIN_CHANGE_THRESHOLD is not set."""
    context.threshold_value = None
    # Remove the env var if it exists
    env = {"MIN_CHANGE_THRESHOLD": ""}
    with patch.dict("os.environ", env, clear=False):
        if "MIN_CHANGE_THRESHOLD" in env:
            del env["MIN_CHANGE_THRESHOLD"]
        import importlib
        import config as config_module

        # Reset to default by reloading with no env var
        original_env = os.environ.get("MIN_CHANGE_THRESHOLD")
        if "MIN_CHANGE_THRESHOLD" in os.environ:
            del os.environ["MIN_CHANGE_THRESHOLD"]
        importlib.reload(config_module)
        context.threshold_config = config_module.Config()
        if original_env:
            os.environ["MIN_CHANGE_THRESHOLD"] = original_env


# ============================================================================
# WHEN STEPS - Actions
# ============================================================================


@when("checking for changes")
def step_check_changes(context):
    """When checking for changes."""
    threshold = getattr(context, "threshold_value", None)
    context.changes = get_portfolio_changes(
        context.current_data, context.previous_data, threshold
    )


# ============================================================================
# THEN STEPS - Assertions
# ============================================================================


@then("no email should be sent because change is below threshold")
def step_no_email_below_threshold(context):
    """No email should be sent because change is below threshold."""
    # Check that there are NO changes in the filtered result
    # This tests that get_portfolio_changes filters by threshold
    threshold = getattr(context, "threshold_value", "0")

    # The test fails because threshold filtering is not implemented
    # Currently ALL changes are returned regardless of magnitude
    assert len(context.changes["increased"]) == 0, (
        f"BUG: Changes below threshold ({threshold}%) should be filtered out. "
        f"Got increased: {context.changes['increased']}"
    )
    assert len(context.changes["decreased"]) == 0, (
        f"BUG: Changes below threshold should be filtered out. "
        f"Got decreased: {context.changes['decreased']}"
    )


@then("email should be sent because change is above threshold")
def step_email_above_threshold(context):
    """Email should be sent because change is above threshold."""
    # There SHOULD be changes returned
    has_changes = (
        len(context.changes["increased"]) > 0
        or len(context.changes["decreased"]) > 0
        or len(context.changes["added"]) > 0
        or len(context.changes["removed"]) > 0
    )

    assert has_changes, (
        f"BUG: Changes above threshold should be included. Got: {context.changes}"
    )


@then("email should be sent because threshold defaults to 0")
def step_email_default_threshold(context):
    """Email should be sent because threshold defaults to 0."""
    # With threshold=0, ANY change should trigger email
    has_changes = (
        len(context.changes["increased"]) > 0 or len(context.changes["decreased"]) > 0
    )

    assert has_changes, (
        "BUG: When threshold is not set, it should default to 0. "
        "Any change should trigger notification. "
        f"Got: {context.changes}"
    )


@then("email should be sent because invalid threshold defaults to 0")
def step_email_invalid_threshold(context):
    """Email should be sent because invalid threshold defaults to 0."""
    # Invalid threshold should be treated as 0
    has_changes = (
        len(context.changes["increased"]) > 0 or len(context.changes["decreased"]) > 0
    )

    assert has_changes, (
        "BUG: Invalid threshold should default to 0. "
        "Any change should trigger notification. "
        f"Got: {context.changes}"
    )


@then("email should be sent because {stock} change is above threshold")
def step_email_stock_above_threshold(context, stock):
    """Email should be sent because a specific stock change is above threshold."""
    # At least one stock should be in the changes
    all_changed = context.changes["increased"] + context.changes["decreased"]

    stock_names = [c["name"] for c in all_changed]

    assert stock in stock_names, (
        f"BUG: {stock} change ({context.threshold_value}% threshold) should be included. "
        f"Got changes: {all_changed}"
    )


@then("{stock} change is below threshold and should be filtered")
def step_stock_filtered(context, stock):
    """A specific stock change is below threshold and should be filtered."""
    # The stock should NOT be in the changes
    all_changed = context.changes["increased"] + context.changes["decreased"]

    stock_names = [c["name"] for c in all_changed]

    assert stock not in stock_names, (
        f"BUG: {stock} change is below threshold and should be filtered out. "
        f"Got changes: {all_changed}"
    )


@then("no email should be sent because decrease is below threshold")
def step_no_email_decrease_below_threshold(context):
    """No email should be sent because decrease is below threshold."""
    # Check that decreased changes are also filtered
    threshold = getattr(context, "threshold_value", "0")

    assert len(context.changes["decreased"]) == 0, (
        f"BUG: Decreases below threshold ({threshold}%) should be filtered out. "
        f"Got decreased: {context.changes['decreased']}"
    )


# ============================================================================
# Import os for the unset test
# ============================================================================
import os
