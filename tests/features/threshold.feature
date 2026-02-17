Feature: Configurable email notification threshold
  As a user
  I want to set a minimum change threshold for email notifications
  So that small portfolio changes don't trigger unnecessary emails

  Background:
    Given the config has MIN_CHANGE_THRESHOLD available

  @happy-path
  Scenario: Small change below threshold should NOT trigger email
    Given the previous portfolio had "AAPL" at "10.0%"
    And the current portfolio has "AAPL" at "10.1%"
    And MIN_CHANGE_THRESHOLD is set to "0.2"
    When checking for changes
    Then no email should be sent because change is below threshold

  @happy-path
  Scenario: Large change above threshold should trigger email
    Given the previous portfolio had "AAPL" at "10.0%"
    And the current portfolio has "AAPL" at "11.0%"
    And MIN_CHANGE_THRESHOLD is set to "0.2"
    When checking for changes
    Then email should be sent because change is above threshold

  @happy-path
  Scenario: No threshold set defaults to 0 (existing behavior)
    Given the previous portfolio had "AAPL" at "10.0%"
    And the current portfolio has "AAPL" at "10.05%"
    And MIN_CHANGE_THRESHOLD is not set
    When checking for changes
    Then email should be sent because threshold defaults to 0

  @edge-case
  Scenario: Negative threshold value should default to 0
    Given the previous portfolio had "AAPL" at "10.0%"
    And the current portfolio has "AAPL" at "10.05%"
    And MIN_CHANGE_THRESHOLD is set to "-1.0"
    When checking for changes
    Then email should be sent because invalid threshold defaults to 0

  @edge-case
  Scenario: Non-numeric threshold should default to 0
    Given the previous portfolio had "AAPL" at "10.0%"
    And the current portfolio has "AAPL" at "10.05%"
    And MIN_CHANGE_THRESHOLD is set to "invalid"
    When checking for changes
    Then email should be sent because invalid threshold defaults to 0

  @edge-case
  Scenario: Threshold applies per stock individually
    Given the previous portfolio had:
      | stock   | weight |
      | AAPL    | 10.0%  |
      | MSFT    | 5.0%   |
    And the current portfolio has:
      | stock   | weight |
      | AAPL    | 10.1%  |
      | MSFT    | 6.0%   |
    And MIN_CHANGE_THRESHOLD is set to "0.5"
    When checking for changes
    Then email should be sent because MSFT change is above threshold
    But AAPL change is below threshold and should be filtered

  @edge-case
  Scenario: Decrease below threshold should NOT trigger email
    Given the previous portfolio had "AAPL" at "10.0%"
    And the current portfolio has "AAPL" at "9.95%"
    And MIN_CHANGE_THRESHOLD is set to "0.2"
    When checking for changes
    Then no email should be sent because decrease is below threshold
