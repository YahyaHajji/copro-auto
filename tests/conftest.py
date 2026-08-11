from __future__ import annotations

import pytest

from copro_auto.domain.models import Project
from sample_projects import build_yasmin_project


@pytest.fixture
def yasmin_project() -> Project:
    return build_yasmin_project()
