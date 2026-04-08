from __future__ import annotations

import builtins
import copy
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import services.base as service_base
from scripts.init_db import initialize_database
from workflows.main_chain import MainChainWorkflow


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DATA_PATH = REPO_ROOT / "data" / "testdata" / "minimal_chain_cases.json"
PROTECTED_DIRS = (
    REPO_ROOT / "runtime",
    REPO_ROOT / "reports",
    REPO_ROOT / "artifacts",
    REPO_ROOT / "data" / "runtime",
)


def _coerce_path(candidate: object) -> Path | None:
    if isinstance(candidate, int):
        return None
    if isinstance(candidate, (str, os.PathLike)):
        return Path(os.fspath(candidate)).resolve()
    return None


def _is_under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def load_case_data() -> dict[str, Any]:
    return json.loads(CASE_DATA_PATH.read_text(encoding="utf-8"))


class IsolatedTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._tempdir = tempfile.TemporaryDirectory()
        self.temp_root = (Path(self._tempdir.name) / "isolated_test_env").resolve()
        self.db_path = (self.temp_root / "data" / "testdata" / "traffic_factory_test.sqlite3").resolve()
        initialize_database(self.db_path)
        self.case_data = load_case_data()

        original_connect = sqlite3.connect
        original_open = builtins.open
        original_io_open = io.open

        def guarded_connect(database: object, *args: object, **kwargs: object):
            if database == ":memory:":
                return original_connect(database, *args, **kwargs)

            path = _coerce_path(database)
            if path is not None and not _is_under(path, self.temp_root):
                raise AssertionError(f"SQLite access outside the injected test temp directory is forbidden: {path}")
            return original_connect(database, *args, **kwargs)

        def guarded_open(file: object, mode: str = "r", *args: object, **kwargs: object):
            path = _coerce_path(file)
            if path is not None and any(_is_under(path, protected) for protected in PROTECTED_DIRS):
                raise AssertionError(f"Protected path access is forbidden during tests: {path}")
            return original_open(file, mode, *args, **kwargs)

        self._patchers = [
            mock.patch("sqlite3.connect", new=guarded_connect),
            mock.patch("builtins.open", new=guarded_open),
            mock.patch("io.open", new=guarded_open),
            mock.patch.object(service_base, "DEFAULT_DB_PATH", self.db_path),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self._patchers):
            patcher.stop()
        self._tempdir.cleanup()
        super().tearDown()

    def make_workflow(self) -> MainChainWorkflow:
        return MainChainWorkflow(db_path=self.db_path)

    def create_chain(
        self,
        workflow: MainChainWorkflow | None = None,
        *,
        content_case: str = "pass",
        create_image: bool = True,
    ) -> dict[str, Any]:
        workflow = workflow or self.make_workflow()
        signal = workflow.discovery_service.create_signal(**copy.deepcopy(self.case_data["signal"]))
        topic = workflow.advance_signal_to_topic(signal_id=signal.id, **copy.deepcopy(self.case_data["topic"]))
        variant = workflow.advance_topic_to_content(
            topic_id=topic.id,
            **copy.deepcopy(self.case_data["content_cases"][content_case]),
        )

        image = None
        if create_image:
            image = workflow.advance_content_to_image(
                content_variant_id=variant.id,
                **copy.deepcopy(self.case_data["image_asset"]),
            )

        return {
            "signal": signal,
            "topic": topic,
            "content_variant": variant,
            "image_asset": image,
        }
