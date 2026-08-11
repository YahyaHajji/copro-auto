from copro_auto.domain.validation import Severity, validate_project


def test_yasmin_project_has_no_blocking_errors(yasmin_project):
    issues = validate_project(yasmin_project)
    assert [issue for issue in issues if issue.severity is Severity.ERROR] == []


def test_duplicate_index_is_blocking(yasmin_project):
    yasmin_project.levels[0].parts[1].index = "1"
    issues = validate_project(yasmin_project)
    assert any(issue.severity is Severity.ERROR and "dupliqué" in issue.message for issue in issues)

