from copro_auto.logging_setup import configure_logging, shutdown_logging


def test_logging_directory_can_be_isolated_for_smoke_tests(tmp_path, monkeypatch):
    monkeypatch.setenv("COPRO_AUTO_LOG_DIR", str(tmp_path))

    try:
        log_file = configure_logging()
    finally:
        shutdown_logging()

    assert log_file == tmp_path / "app.log"
    assert log_file.exists()
