from copro_auto.projects.json_repository import JsonProjectRepository, project_to_dict


def test_json_roundtrip_is_lossless(tmp_path, yasmin_project):
    repository = JsonProjectRepository()
    path = tmp_path / "yasmin.copro.json"
    repository.save(yasmin_project, path)
    loaded = repository.load(path)
    assert project_to_dict(loaded) == project_to_dict(yasmin_project)
    assert not list(tmp_path.glob("*.tmp"))

