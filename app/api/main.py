from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.api.base import JsonDict, RouteRegistration, error_response
from app.api.routes import (
    ContentRouteSet,
    ImageRouteSet,
    PublishCheckRouteSet,
    RetroRouteSet,
    SignalRouteSet,
    TopicRouteSet,
)


@dataclass(frozen=True, slots=True)
class RouteView:
    method: str
    path: str
    summary: str


class MinimalApiApplication:
    def __init__(self, *, db_path: str | Path | None = None):
        self._routes: list[RouteRegistration] = []
        for route_set in (
            SignalRouteSet(db_path=db_path),
            TopicRouteSet(db_path=db_path),
            ContentRouteSet(db_path=db_path),
            ImageRouteSet(db_path=db_path),
            PublishCheckRouteSet(db_path=db_path),
            RetroRouteSet(db_path=db_path),
        ):
            self._routes.extend(route_set.routes())

    def list_routes(self) -> list[RouteView]:
        return [RouteView(route.method, route.path, route.summary) for route in self._routes]

    def handle(
        self,
        *,
        method: str,
        path: str,
        payload: JsonDict | None = None,
        query: JsonDict | None = None,
    ) -> JsonDict:
        normalized_method = method.strip().upper()
        normalized_path = self._normalize_path(path)
        payload = dict(payload or {})
        query = dict(query or {})

        for route in self._routes:
            if route.method != normalized_method:
                continue
            params = self._match_path(route.path, normalized_path)
            if params is None:
                continue
            return route.handler(payload, query, params)

        return error_response("ROUTE_NOT_FOUND", f"No route for {normalized_method} {normalized_path}")

    @staticmethod
    def _normalize_path(path: str) -> str:
        if not path:
            return "/"
        normalized = "/" + path.strip().strip("/")
        return "/" if normalized == "//" else normalized

    @staticmethod
    def _match_path(route_path: str, actual_path: str) -> JsonDict | None:
        route_parts = [part for part in route_path.strip("/").split("/") if part]
        actual_parts = [part for part in actual_path.strip("/").split("/") if part]

        if len(route_parts) != len(actual_parts):
            return None

        params: JsonDict = {}
        for route_part, actual_part in zip(route_parts, actual_parts):
            if route_part.startswith("{") and route_part.endswith("}"):
                key = route_part[1:-1].strip()
                if not key:
                    return None
                params[key] = actual_part
                continue
            if route_part != actual_part:
                return None
        return params


def create_application(*, db_path: str | Path | None = None) -> MinimalApiApplication:
    return MinimalApiApplication(db_path=db_path)
