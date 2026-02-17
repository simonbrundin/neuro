Feature: Get portfolio data from NeuroQuant
  As a developer
  I want to fetch portfolio data without race conditions
  So that correct portfolio data is saved properly

  Background:
    Given the scraper is configured with test credentials
    And I have a mocked browser page

  @happy-path
  Scenario: Use wait_for_selector instead of asyncio.sleep for dropdown
    Given the scraper is on the portfolio page
    When get_portfolio_data() is called
    Then it should NOT use asyncio.sleep() to wait for dropdown
    But should use wait_for_selector() instead

  @happy-path
  Scenario: Verify portfolio after selection
    Given a wrong portfolio was initially selected
    When get_portfolio_data() runs
    Then it should verify that correct portfolio is selected
    And should call wait_for_selector again to confirm

  @edge-case
  Scenario: Retry logic with exponential backoff
    Given the portfolio selection fails
    When get_portfolio_data() is called
    Then it should retry with exponential backoff

  @edge-case
  Scenario: Log portfolio confirmation
    Given the correct portfolio has been fetched successfully
    When get_portfolio_data() completes
    Then it should log a confirmation message

  @edge-case
  Scenario: Use wait_for_selector for date not sleep
    Given the portfolio is selected
    When the date element is fetched
    Then it should use wait_for_selector() not asyncio.sleep()

  @regression
  Scenario: Summary of all bugs
    Given the scraper is on the portfolio page
    When get_portfolio_data() is called
    Then it should not use asyncio.sleep() for waiting
    And it should verify portfolio after selection
    And it should have retry logic with exponential backoff
    And it should log confirmation for portfolio
