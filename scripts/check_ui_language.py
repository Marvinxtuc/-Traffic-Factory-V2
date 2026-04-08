#!/usr/bin/env python3
"""Check V1 web pages for hardcoded English UI copy.

Usage:
  python3 scripts/check_ui_language.py
  python3 scripts/check_ui_language.py v1/web/discovery.html v1/web/assets/ui.js
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from html.parser import HTMLParser
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = [
    "v1/web/discovery.html",
    "v1/web/topics.html",
    "v1/web/content.html",
    "v1/web/assets/ui.js",
]

ALLOWED_ENGLISH = {"rss", "json", "v1", "v1.0.4"}
INTERNAL_ENUMS = {
    "new",
    "reviewed",
    "converted",
    "archived",
    "pending",
    "in_progress",
    "done",
    "dropped",
    "queued",
    "generating",
    "completed",
    "failed",
    "rss",
    "web",
    "manual",
    "wechat_article",
}

BANNED_UI_PHRASES = [
    "discovery",
    "topic pool",
    "content lab",
    "signal feed",
    "signal analysis",
    "metadata",
    "operation result",
    "all sources",
    "all status",
    "loading",
    "error",
    "retry",
    "refresh",
    "close",
    "start writing",
    "regenerate",
    "edit angle",
    "wechat",
]

ALLOWED_INTERNAL_PHRASES = {
    "unknown error",
    "topic not found",
    "signal not found",
    "failed to fetch",
}

STRING_LITERAL_RE = re.compile(r"(?:'([^'\\]*(?:\\.[^'\\]*)*)'|\"([^\"\\]*(?:\\.[^\"\\]*)*)\"|`([^`\\]*(?:\\.[^`\\]*)*)`)")
ENGLISH_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*")


class HTMLExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_script = False
        self.visible_text: list[tuple[int, str]] = []
        self.script_text: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "script":
            self.in_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self.in_script = False

    def handle_data(self, data: str) -> None:
        if not data or not data.strip():
            return
        line = self.getpos()[0]
        if self.in_script:
            self.script_text.append((line, data))
        else:
            self.visible_text.append((line, data.strip()))


def is_allowed_word(word: str) -> bool:
    lowered = word.lower()
    if lowered in ALLOWED_ENGLISH:
        return True
    if lowered in INTERNAL_ENUMS:
        return True
    if lowered.startswith("v") and re.fullmatch(r"v\d+(?:\.\d+)*", lowered):
        return True
    return False


def should_skip_script_literal(text: str) -> bool:
    raw = text.strip()
    if not raw:
        return True
    if len(raw) < 3:
        return True
    if re.fullmatch(r"[A-Z0-9_]+(?:\.[A-Z0-9_]+)+", raw):
        return True
    if "t('" in raw or 't("' in raw:
        return True
    if "<" in raw or ">" in raw:
        return True
    if raw.startswith(("/", "#", ".", "[")):
        return True
    if re.fullmatch(r"[a-z0-9_./?&=:-]+", raw):
        return True
    if raw.startswith("--"):
        return True
    return False


def collect_visible_english(path: pathlib.Path, text: str) -> list[str]:
    parser = HTMLExtractor()
    parser.feed(text)

    warnings: list[str] = []

    for line, segment in parser.visible_text:
        words = ENGLISH_WORD_RE.findall(segment)
        bad = [w for w in words if not is_allowed_word(w)]
        if bad:
            warnings.append(f"{path}:{line}: 可见文案含英文: {segment}")

    for line, script_block in parser.script_text:
        for literal in extract_string_literals(script_block):
            if should_skip_script_literal(literal):
                continue
            lowered = literal.lower()
            if any(phrase in lowered for phrase in BANNED_UI_PHRASES):
                warnings.append(f"{path}:{line}: 脚本文案疑似英文 UI: {literal}")

    return warnings


def extract_string_literals(js_text: str) -> Iterable[str]:
    for match in STRING_LITERAL_RE.finditer(js_text):
        content = match.group(1) or match.group(2) or match.group(3) or ""
        content = bytes(content, "utf-8").decode("unicode_escape")
        yield content.strip()


def collect_js_english(path: pathlib.Path, text: str) -> list[str]:
    warnings: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for literal in extract_string_literals(line):
            if should_skip_script_literal(literal):
                continue
            lowered = literal.lower()
            if lowered in ALLOWED_INTERNAL_PHRASES:
                continue
            if any(phrase in lowered for phrase in BANNED_UI_PHRASES):
                warnings.append(f"{path}:{idx}: 脚本文案疑似英文 UI: {literal}")
    return warnings


def resolve_targets(raw_targets: list[str]) -> list[pathlib.Path]:
    targets = raw_targets if raw_targets else DEFAULT_TARGETS
    resolved: list[pathlib.Path] = []
    for target in targets:
        path = (ROOT / target).resolve() if not pathlib.Path(target).is_absolute() else pathlib.Path(target)
        if path.exists():
            resolved.append(path)
        else:
            print(f"[WARN] 目标不存在: {target}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 V1 前端英文 UI 文案残留")
    parser.add_argument("targets", nargs="*", help="待扫描文件，默认扫描 V1 三页面与 ui.js")
    args = parser.parse_args()

    targets = resolve_targets(args.targets)
    if not targets:
        print("未找到可扫描文件。")
        return 1

    warnings: list[str] = []

    for path in targets:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".html":
            warnings.extend(collect_visible_english(path, text))
        elif path.suffix.lower() == ".js":
            warnings.extend(collect_js_english(path, text))

    if warnings:
        print("发现英文 UI 残留或疑似项：")
        for item in warnings:
            print(f"- {item}")
        return 1

    print("检查通过：未发现英文 UI 可见文案残留。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
