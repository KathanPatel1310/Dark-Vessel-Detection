"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolated_case_store(tmp_path_factory):
    """Keep persisted investigation files from tests out of data/processed/cases."""
    import src.api.server as server

    original = server.CASES_DIR
    server.CASES_DIR = str(tmp_path_factory.mktemp("cases"))
    yield
    server.CASES_DIR = original
