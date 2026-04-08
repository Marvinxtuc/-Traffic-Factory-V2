from __future__ import annotations

import os

SSL_FALLBACK_ENV_KEY = "TF_V1_ALLOW_INSECURE_SSL_FALLBACK"


def allow_insecure_ssl_fallback() -> bool:
    raw = os.environ.get(SSL_FALLBACK_ENV_KEY, "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}
