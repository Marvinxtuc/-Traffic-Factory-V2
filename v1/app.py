from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from urllib3.exceptions import InsecureRequestWarning
import urllib3

from v1.contracts import ContentJobStatus, SignalStatus, SourceType, TopicStatus
from v1.db import DEFAULT_DB_PATH, connect_db, init_db
from v1.ingestion import normalize_signal
from v1.repository import (
    create_content_version,
    create_content_job,
    create_topic_from_signal,
    get_content_version,
    get_signal,
    get_topic,
    list_content_versions,
    list_signals,
    list_topics,
    save_signal,
    update_content_job_status,
    update_signal_status,
    update_topic_status,
    upsert_source,
)
from v1.security import SSL_FALLBACK_ENV_KEY, allow_insecure_ssl_fallback

DB_PATH = Path(os.environ.get("TF_V1_DB_PATH", str(DEFAULT_DB_PATH)))
WEB_DIR = Path(__file__).resolve().parent / "web"
WEB_ASSETS_DIR = WEB_DIR / "assets"
urllib3.disable_warnings(InsecureRequestWarning)

app = FastAPI(
    title="Traffic Factory V1 Base",
    version="1.0.0",
    description="Round 2 contract-hardened base for signal ingestion and topic decisions.",
)
app.mount("/web/assets", StaticFiles(directory=WEB_ASSETS_DIR), name="web-assets")


class ManualSignalRequest(BaseModel):
    source_name: str = Field(default="manual_input", min_length=1)
    title: str = Field(min_length=1)
    summary: str | None = None
    content_raw: str | None = None
    canonical_url: str | None = None
    author: str | None = None
    published_at: str | None = None
    lang: str | None = "unknown"
    tags: list[str] | None = None
    status: SignalStatus = SignalStatus.NEW


class RssIngestRequest(BaseModel):
    source_name: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    max_items: int = Field(default=20, ge=1, le=100)
    status: SignalStatus = SignalStatus.NEW


class WebIngestRequest(BaseModel):
    source_url: str = Field(min_length=1)
    source_name: str | None = None
    lang: str | None = "unknown"
    status: SignalStatus = SignalStatus.NEW


class TopicFromSignalRequest(BaseModel):
    topic_title: str | None = None
    angle: str | None = None
    target_platform: str | None = "general"
    commercial_value: float = 0.0


class GenerateContentRequest(BaseModel):
    topic_id: int
    content_type: str = Field(default="article", min_length=1)
    input_payload: dict[str, Any] | None = None


@app.on_event("startup")
def on_startup() -> None:
    init_db(DB_PATH)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/web/discovery")


@app.get("/web/discovery")
def discovery_page() -> FileResponse:
    return FileResponse(WEB_DIR / "discovery.html")


@app.get("/web/topics")
def topics_page() -> FileResponse:
    return FileResponse(WEB_DIR / "topics.html")


@app.get("/web/content")
def content_page() -> FileResponse:
    return FileResponse(WEB_DIR / "content.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/signals")
def get_signals(
    source_type: SourceType | None = Query(default=None),
    status: SignalStatus | None = Query(default=None),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        items = list_signals(
            conn,
            source_type=source_type.value if source_type else None,
            status=status.value if status else None,
            order=order,
            limit=limit,
        )
    return {"items": items, "count": len(items)}


@app.post("/signals/{signal_id}/review")
def review_signal(signal_id: int) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        signal = get_signal(conn, signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        if signal["status"] != SignalStatus.NEW.value:
            raise HTTPException(
                status_code=409,
                detail=f"Signal review requires status new, got {signal['status']}",
            )
        try:
            updated = update_signal_status(
                conn,
                signal_id=signal_id,
                target_status=SignalStatus.REVIEWED,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        conn.commit()
    return {"signal": updated}


@app.post("/signals/manual")
def create_manual_signal(payload: ManualSignalRequest) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        source_id = upsert_source(
            conn,
            source_type=SourceType.MANUAL.value,
            source_name=payload.source_name,
            source_url=None,
        )

        normalized = normalize_signal(
            source_type=SourceType.MANUAL.value,
            source_name=payload.source_name,
            source_id=source_id,
            title=payload.title,
            summary=payload.summary,
            content_raw=payload.content_raw,
            canonical_url=payload.canonical_url,
            author=payload.author,
            published_at=payload.published_at,
            external_id=None,
            lang=payload.lang,
            tags=payload.tags,
            status=payload.status.value,
        )

        signal_id, inserted = save_signal(conn, normalized)
        signal = get_signal(conn, signal_id)
        conn.commit()

    return {
        "inserted": inserted,
        "signal": signal,
    }


@app.post("/signals/ingest/rss")
def ingest_rss(payload: RssIngestRequest) -> dict[str, Any]:
    parsed = feedparser.parse(payload.source_url)
    entries = list(parsed.entries or [])[: payload.max_items]
    if not entries:
        raise HTTPException(status_code=400, detail="RSS feed contains no entries")

    inserted_ids: list[int] = []
    skipped_ids: list[int] = []

    with connect_db(DB_PATH) as conn:
        source_id = upsert_source(
            conn,
            source_type=SourceType.RSS.value,
            source_name=payload.source_name,
            source_url=payload.source_url,
        )

        for entry in entries:
            title = str(entry.get("title", "")).strip()
            if not title:
                continue

            content_raw = ""
            entry_content = entry.get("content", [])
            if isinstance(entry_content, list) and entry_content:
                first_content = entry_content[0]
                if isinstance(first_content, dict):
                    content_raw = str(first_content.get("value", ""))

            tag_list: list[str] = []
            raw_tags = entry.get("tags", [])
            if isinstance(raw_tags, list):
                for raw_tag in raw_tags:
                    if isinstance(raw_tag, dict):
                        term = str(raw_tag.get("term", "")).strip()
                        if term:
                            tag_list.append(term)

            normalized = normalize_signal(
                source_type=SourceType.RSS.value,
                source_name=payload.source_name,
                source_id=source_id,
                title=title,
                summary=str(entry.get("summary") or entry.get("description") or ""),
                content_raw=content_raw,
                canonical_url=str(entry.get("link") or ""),
                author=str(entry.get("author") or ""),
                published_at=str(entry.get("published") or entry.get("updated") or ""),
                external_id=str(entry.get("id") or entry.get("link") or ""),
                lang=None,
                tags=tag_list,
                status=payload.status.value,
            )

            signal_id, inserted = save_signal(conn, normalized)
            if inserted:
                inserted_ids.append(signal_id)
            else:
                skipped_ids.append(signal_id)

        conn.commit()

    return {
        "source_name": payload.source_name,
        "source_url": payload.source_url,
        "total_entries": len(entries),
        "inserted_count": len(inserted_ids),
        "skipped_count": len(skipped_ids),
        "inserted_signal_ids": inserted_ids,
        "skipped_signal_ids": skipped_ids,
    }


@app.post("/signals/ingest/web")
def ingest_web(payload: WebIngestRequest) -> dict[str, Any]:
    ssl_verified = True
    ssl_fallback_used = False
    allow_fallback = allow_insecure_ssl_fallback()
    try:
        response = requests.get(
            payload.source_url,
            timeout=15,
            headers={"User-Agent": "TrafficFactoryV1/1.0"},
        )
        response.raise_for_status()
    except requests.exceptions.SSLError as exc:
        if not allow_fallback:
            raise HTTPException(
                status_code=502,
                detail=(
                    "SSL verification failed. "
                    f"Set {SSL_FALLBACK_ENV_KEY}=1 to explicitly allow insecure fallback."
                ),
            ) from exc
        ssl_verified = False
        ssl_fallback_used = True
        try:
            response = requests.get(
                payload.source_url,
                timeout=15,
                headers={"User-Agent": "TrafficFactoryV1/1.0"},
                verify=False,
            )
            response.raise_for_status()
        except requests.RequestException as retry_exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch webpage: {retry_exc}") from retry_exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch webpage: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.extract()

    title = (soup.title.string or "").strip() if soup.title else ""
    summary_meta = soup.find("meta", attrs={"name": "description"})
    summary = summary_meta.get("content", "").strip() if summary_meta else ""

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if p]
    content_raw = "\n".join(paragraphs[:30])
    if not content_raw:
        content_raw = soup.get_text(" ", strip=True)

    source_name = payload.source_name or urlparse(payload.source_url).netloc or "web_source"

    with connect_db(DB_PATH) as conn:
        source_id = upsert_source(
            conn,
            source_type=SourceType.WEB.value,
            source_name=source_name,
            source_url=payload.source_url,
        )

        normalized = normalize_signal(
            source_type=SourceType.WEB.value,
            source_name=source_name,
            source_id=source_id,
            title=title or payload.source_url,
            summary=summary,
            content_raw=content_raw,
            canonical_url=payload.source_url,
            author=None,
            published_at=None,
            external_id=payload.source_url,
            lang=payload.lang,
            tags=None,
            status=payload.status.value,
        )

        signal_id, inserted = save_signal(conn, normalized)
        signal = get_signal(conn, signal_id)
        conn.commit()

    return {
        "inserted": inserted,
        "ssl_verified": ssl_verified,
        "ssl_fallback_used": ssl_fallback_used,
        "ssl_fallback_enabled": allow_fallback,
        "signal": signal,
    }


@app.post("/topics/from-signal/{signal_id}")
def add_signal_to_topic_pool(signal_id: int, payload: TopicFromSignalRequest | None = None) -> dict[str, Any]:
    payload = payload or TopicFromSignalRequest()

    with connect_db(DB_PATH) as conn:
        signal = get_signal(conn, signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")

        try:
            topic_id, created = create_topic_from_signal(
                conn,
                signal_id=signal_id,
                topic_title=payload.topic_title or signal["title"],
                angle=payload.angle,
                target_platform=payload.target_platform,
                commercial_value=payload.commercial_value,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        topic = get_topic(conn, topic_id)
        conn.commit()

    return {
        "created": created,
        "topic": topic,
    }


@app.get("/topics")
def get_topics(limit: int = Query(default=100, ge=1, le=200)) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        items = list_topics(conn, limit=limit)
    return {"items": items, "count": len(items)}


def _update_topic_status_with_guard(
    topic_id: int,
    *,
    target_status: TopicStatus,
    allowed_current: set[TopicStatus],
) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        topic = get_topic(conn, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        current_status = TopicStatus(topic["status"])
        if current_status not in allowed_current:
            allowed_values = ", ".join(status.value for status in sorted(allowed_current, key=lambda item: item.value))
            raise HTTPException(
                status_code=409,
                detail=f"Topic transition requires status in [{allowed_values}], got {current_status.value}",
            )
        try:
            updated = update_topic_status(
                conn,
                topic_id=topic_id,
                target_status=target_status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        conn.commit()
    return updated


@app.post("/topics/{topic_id}/start")
def start_topic(topic_id: int) -> dict[str, Any]:
    updated = _update_topic_status_with_guard(
        topic_id,
        target_status=TopicStatus.IN_PROGRESS,
        allowed_current={TopicStatus.PENDING},
    )
    return {"topic": updated}


@app.post("/topics/{topic_id}/complete")
def complete_topic(topic_id: int) -> dict[str, Any]:
    updated = _update_topic_status_with_guard(
        topic_id,
        target_status=TopicStatus.DONE,
        allowed_current={TopicStatus.IN_PROGRESS},
    )
    return {"topic": updated}


@app.post("/topics/{topic_id}/drop")
def drop_topic(topic_id: int) -> dict[str, Any]:
    updated = _update_topic_status_with_guard(
        topic_id,
        target_status=TopicStatus.DROPPED,
        allowed_current={TopicStatus.PENDING, TopicStatus.IN_PROGRESS},
    )
    return {"topic": updated}


@app.post("/content/generate")
def generate_content(payload: GenerateContentRequest) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        topic = get_topic(conn, payload.topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        model_input = {
            "topic_id": payload.topic_id,
            "topic_title": topic["topic_title"],
            "content_type": payload.content_type,
            "extra": payload.input_payload or {},
        }
        content_job = create_content_job(
            conn,
            topic_id=payload.topic_id,
            content_type=payload.content_type,
            input_payload=model_input,
            output_payload=None,
            status=ContentJobStatus.QUEUED,
        )
        try:
            content_job = update_content_job_status(
                conn,
                job_id=content_job["id"],
                target_status=ContentJobStatus.GENERATING,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        model_output = {
            "mode": "mock",
            "headline": topic["topic_title"],
            "structure": [
                "Problem statement",
                "Signal summary",
                "Actionable angle",
                "Call to action",
            ],
            "draft": f"[MOCK] {topic['topic_title']} - {payload.content_type}",
        }

        try:
            content_job = update_content_job_status(
                conn,
                job_id=content_job["id"],
                target_status=ContentJobStatus.COMPLETED,
                output_payload=model_output,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        content_text = str(model_output.get("draft") or "").strip()
        if not content_text:
            content_text = json.dumps(model_output, ensure_ascii=False)
        version = create_content_version(
            conn,
            topic_id=payload.topic_id,
            content_type=payload.content_type,
            content_text=content_text,
            meta={
                "runtime_smoke": bool((payload.input_payload or {}).get("runtime_smoke", False)),
                "headline": model_output.get("headline"),
                "structure": model_output.get("structure"),
                "source_job_id": content_job["id"],
                "job_status": content_job["status"],
            },
        )
        conn.commit()

    return {
        "job": content_job,
        "result": content_job["output_payload"],
        "version": version,
    }


@app.get("/content/versions")
def get_content_versions(
    topic_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        items = list_content_versions(conn, topic_id=topic_id, limit=limit)
    return {"items": items, "count": len(items)}


@app.get("/content/versions/{version_id}")
def get_content_version_detail(version_id: int) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        item = get_content_version(conn, version_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content version not found")
    return {"version": item}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("v1.app:app", host="127.0.0.1", port=8788, reload=False)
