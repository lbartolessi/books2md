# -*- coding: utf-8 -*-
"""
Global Pytest Configuration and Fixtures
=========================================

This file provides shared fixtures and helper functions accessible to all
test suites in the project.
"""

import pytest
from bs4 import BeautifulSoup


@pytest.fixture
def assert_html_equal():
    """Provides a helper to compare two HTML strings for structural equality."""

    def _assert_html_equal(actual_str: str, expected_str: str) -> None:
        actual_soup = BeautifulSoup(actual_str, "lxml")
        expected_soup = BeautifulSoup(expected_str, "lxml")
        assert actual_soup.prettify() == expected_soup.prettify()

    return _assert_html_equal
