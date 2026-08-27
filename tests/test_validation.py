from copro_auto.domain.validation import Severity, validate_project
from decimal import Decimal


def test_yasmin_project_has_no_blocking_errors(yasmin_project):
    issues = validate_project(yasmin_project)
    assert [issue for issue in issues if issue.severity is Severity.ERROR] == []


def test_duplicate_index_is_blocking(yasmin_project):
    yasmin_project.levels[0].parts[1].index = "1"
    issues = validate_project(yasmin_project)
    assert any(issue.severity is Severity.ERROR and "dupliqué" in issue.message for issue in issues)


def test_same_private_index_is_allowed_on_different_levels(yasmin_project):
    repeated_index = yasmin_project.levels[0].parts[0].index
    yasmin_project.levels[1].parts[0].index = repeated_index

    issues = validate_project(yasmin_project)

    assert not any("dupliqué" in issue.message for issue in issues)


def test_multiple_measurements_are_valid_when_every_end_is_above_every_start(yasmin_project):
    level = yasmin_project.levels[0]
    level.start_elevations = (Decimal("0.00"), Decimal("0.60"))
    level.end_elevations = (Decimal("3.60"),)
    level.interior_heights = (Decimal("3.60"), Decimal("3.00"))

    issues = validate_project(yasmin_project)

    assert not any(issue.field.endswith(("start_elevations", "end_elevations", "interior_heights")) for issue in issues)


def test_missing_start_invalid_end_and_nonpositive_height_are_blocking(yasmin_project):
    level = yasmin_project.levels[0]
    level.start_elevations = ()
    level.end_elevations = (Decimal("0.20"),)
    level.interior_heights = (Decimal("0"), Decimal("-1"))

    issues = validate_project(yasmin_project)

    assert any(issue.severity is Severity.ERROR and issue.field.endswith("start_elevations") for issue in issues)
    assert any(issue.severity is Severity.ERROR and issue.field.endswith("interior_heights") for issue in issues)

    level.start_elevations = (Decimal("0.20"), Decimal("0.60"))
    level.end_elevations = (Decimal("0.60"), Decimal("3.10"))
    issues = validate_project(yasmin_project)
    assert any(issue.severity is Severity.ERROR and issue.field.endswith("end_elevations") for issue in issues)
