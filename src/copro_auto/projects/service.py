from __future__ import annotations

from pathlib import Path

from copro_auto.domain.models import Project, ProjectIdentity
from copro_auto.domain.validation import ValidationIssue, validate_project

from .json_repository import JsonProjectRepository


class ProjectService:
    def __init__(self, repository: JsonProjectRepository | None = None) -> None:
        self.repository = repository or JsonProjectRepository()

    def new(self, identity: ProjectIdentity) -> Project:
        return Project(identity=identity)

    def open(self, path: str | Path) -> Project:
        return self.repository.load(path)

    def save(self, project: Project, path: str | Path) -> Path:
        return self.repository.save(project, path)

    def validate(self, project: Project) -> list[ValidationIssue]:
        return validate_project(project)

