from copy import deepcopy

import pytest

from copro_auto.projects.json_repository import (
    CURRENT_SCHEMA_VERSION,
    JsonProjectRepository,
    project_from_dict,
    project_to_dict,
)


def _convert_levels_to_legacy_scalars(data):
    for level in data["levels"]:
        starts = level.pop("start_elevations")
        ends = level.pop("end_elevations")
        heights = level.pop("interior_heights")
        level["start_elevation"] = starts[0]
        level["end_elevation"] = ends[0] if ends else None
        level["interior_height"] = heights[0] if heights else None


def test_json_roundtrip_is_lossless(tmp_path, yasmin_project):
    repository = JsonProjectRepository()
    path = tmp_path / "yasmin.copro.json"
    repository.save(yasmin_project, path)
    loaded = repository.load(path)
    assert project_to_dict(loaded) == project_to_dict(yasmin_project)
    assert not list(tmp_path.glob("*.tmp"))


def test_schema_v1_is_migrated_without_losing_existing_business_data(yasmin_project):
    legacy = deepcopy(project_to_dict(yasmin_project))
    legacy["schema_version"] = 1
    _convert_levels_to_legacy_scalars(legacy)
    for key in ("project_time", "land_registry_office", "client"):
        legacy["identity"].pop(key)
    legacy["identity"]["boundaries"] = {}
    migrated = project_from_dict(legacy)
    assert migrated.schema_version == CURRENT_SCHEMA_VERSION
    assert migrated.identity.land_title == yasmin_project.identity.land_title
    assert migrated.identity.project_time.isoformat(timespec="minutes") == "10:00"
    assert migrated.identity.client.full_name == ""
    assert [level.id for level in migrated.levels] == [level.id for level in yasmin_project.levels]
    assert project_to_dict(migrated)["schema_version"] == CURRENT_SCHEMA_VERSION


@pytest.mark.parametrize("legacy_version", (2, 3))
def test_schema_v2_and_v3_scalar_measurements_are_migrated_to_v4_tuples(
    yasmin_project, legacy_version
):
    legacy = deepcopy(project_to_dict(yasmin_project))
    legacy["schema_version"] = legacy_version
    _convert_levels_to_legacy_scalars(legacy)

    migrated = project_from_dict(legacy)

    assert migrated.schema_version == 4
    assert migrated.levels[0].start_elevations == (migrated.levels[0].start_elevation,)
    assert migrated.levels[0].end_elevations == (migrated.levels[0].end_elevation,)
    assert migrated.levels[0].interior_heights == (migrated.levels[0].interior_height,)


def test_schema_v4_roundtrip_preserves_ordered_multiple_measurements(tmp_path, yasmin_project):
    level = yasmin_project.levels[0]
    level.start_elevations = (level.start_elevation,)
    level.end_elevations = (level.end_elevation, level.end_elevation + 2)
    level.interior_heights = (level.interior_height, level.interior_height + 2)

    path = tmp_path / "multi-values.copro.json"
    repository = JsonProjectRepository()
    repository.save(yasmin_project, path)
    loaded = repository.load(path)

    assert loaded.levels[0].start_elevations == (level.start_elevation,)
    assert loaded.levels[0].end_elevations == level.end_elevations
    assert loaded.levels[0].interior_heights == level.interior_heights
