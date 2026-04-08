from __future__ import annotations

try:
    import pytest
except ModuleNotFoundError:  # pragma: no cover - used only when pytest exists locally
    pytest = None

if pytest is not None:  # pragma: no cover - optional compatibility layer
    import builtins
    import copy
    import io
    import sqlite3
    from pathlib import Path

    import services.base as service_base
    from tests.support import CASE_DATA_PATH, PROTECTED_DIRS, REPO_ROOT, _coerce_path, _is_under, load_case_data
    from workflows.main_chain import MainChainWorkflow
    from scripts.init_db import initialize_database

    @pytest.fixture
    def repo_root() -> Path:
        return REPO_ROOT

    @pytest.fixture
    def case_data():
        return load_case_data()

    @pytest.fixture(autouse=True)
    def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        temp_root = (tmp_path / "isolated_test_env").resolve()
        db_path = (temp_root / "data" / "testdata" / "traffic_factory_test.sqlite3").resolve()
        initialize_database(db_path)

        original_connect = sqlite3.connect
        original_open = builtins.open
        original_io_open = io.open

        def guarded_connect(database: object, *args: object, **kwargs: object):
            if database == ":memory:":
                return original_connect(database, *args, **kwargs)

            path = _coerce_path(database)
            if path is not None and not _is_under(path, temp_root):
                raise AssertionError(
                    f"SQLite access outside the injected test temp directory is forbidden: {path}"
                )
            return original_connect(database, *args, **kwargs)

        def guarded_open(file: object, mode: str = "r", *args: object, **kwargs: object):
            path = _coerce_path(file)
            if path is not None and any(_is_under(path, protected) for protected in PROTECTED_DIRS):
                raise AssertionError(f"Protected path access is forbidden during tests: {path}")
            return original_open(file, mode, *args, **kwargs)

        monkeypatch.setattr(sqlite3, "connect", guarded_connect)
        monkeypatch.setattr(builtins, "open", guarded_open)
        monkeypatch.setattr(io, "open", guarded_open)
        monkeypatch.setattr(service_base, "DEFAULT_DB_PATH", db_path)

        return {"repo_root": REPO_ROOT, "temp_root": temp_root, "db_path": db_path}

    @pytest.fixture
    def workflow(isolated_environment):
        return MainChainWorkflow(db_path=isolated_environment["db_path"])

    @pytest.fixture
    def repository(workflow: MainChainWorkflow):
        return workflow.discovery_service.repository

    @pytest.fixture
    def create_chain(workflow: MainChainWorkflow, case_data):
        def _create_chain(*, content_case: str = "pass", create_image: bool = True):
            signal = workflow.discovery_service.create_signal(**copy.deepcopy(case_data["signal"]))
            topic = workflow.advance_signal_to_topic(signal_id=signal.id, **copy.deepcopy(case_data["topic"]))
            variant = workflow.advance_topic_to_content(
                topic_id=topic.id,
                **copy.deepcopy(case_data["content_cases"][content_case]),
            )

            image = None
            if create_image:
                image = workflow.advance_content_to_image(
                    content_variant_id=variant.id,
                    **copy.deepcopy(case_data["image_asset"]),
                )

            return {
                "signal": signal,
                "topic": topic,
                "content_variant": variant,
                "image_asset": image,
            }

        return _create_chain
