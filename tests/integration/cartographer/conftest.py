"""Skip cartographer integration tests when ROBOFLOW_API_KEY is unset.

Tests in this directory hit the live Roboflow inference endpoint and are
gated on @pytest.mark.requires_roboflow_api_key. When the env var is missing
they skip cleanly so contributors without a key still pass locally.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

import pytest


def pytest_collection_modifyitems(
    config: pytest.Config, items: Iterable[pytest.Item]
) -> None:
    if os.environ.get("ROBOFLOW_API_KEY"):
        return
    skip_marker = pytest.mark.skip(reason="ROBOFLOW_API_KEY env var is unset")
    for item in items:
        if "requires_roboflow_api_key" in item.keywords:
            item.add_marker(skip_marker)
