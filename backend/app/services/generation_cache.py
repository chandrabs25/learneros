from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any
from urllib import parse as urlparse
from urllib import request as urlrequest

from app.observability import trace_exception


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    payload: Any
    expires_at: float


class TTLGenerationCache:
    """In-process LRU cache with TTL."""

    def __init__(self, *, max_entries: int, default_ttl_seconds: int) -> None:
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return entry.payload

    def set(self, key: str, payload: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = time.time() + max(1, ttl)
        with self._lock:
            self._entries[key] = CacheEntry(payload=payload, expires_at=expires_at)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
                self._evictions += 1

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._entries),
                "evictions": self._evictions,
            }


def stable_cache_key(endpoint: str, values: dict[str, Any]) -> str:
    canonical = {"endpoint": endpoint, **values}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class GenerationCache(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None: ...

    @abstractmethod
    def set(self, key: str, payload: Any, ttl_seconds: int | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def stats(self) -> dict[str, Any]: ...


class UpstashRedisClient:
    def __init__(self, *, base_url: str, token: str, timeout_seconds: float = 1.5) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _call(self, path: str) -> dict[str, Any] | None:
        req = urlrequest.Request(
            url=f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self.token}"},
            method="GET",
        )
        with urlrequest.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def get(self, key: str) -> str | None:
        safe_key = urlparse.quote(key, safe="")
        data = self._call(f"/get/{safe_key}")
        result = (data or {}).get("result")
        if result is None:
            return None
        return str(result)

    def setex(self, key: str, value: str, ttl_seconds: int) -> None:
        safe_key = urlparse.quote(key, safe="")
        safe_val = urlparse.quote(value, safe="")
        ttl = max(1, int(ttl_seconds))
        self._call(f"/set/{safe_key}/{safe_val}?EX={ttl}")

    def delete(self, key: str) -> None:
        safe_key = urlparse.quote(key, safe="")
        self._call(f"/del/{safe_key}")


class HybridGenerationCache(GenerationCache):
    """
    Local LRU+TTL cache with optional Upstash Redis backing.
    Local cache is always checked first for low latency.
    """

    def __init__(
        self,
        *,
        local_cache: TTLGenerationCache,
        remote: UpstashRedisClient | None = None,
        default_ttl_seconds: int = 604800,
    ) -> None:
        self.local = local_cache
        self.remote = remote
        self.default_ttl_seconds = default_ttl_seconds
        self._remote_hits = 0
        self._remote_misses = 0
        self._remote_errors = 0

    def get(self, key: str) -> Any | None:
        local = self.local.get(key)
        if local is not None:
            return local
        if self.remote is None:
            return None
        try:
            raw = self.remote.get(key)
            if raw is None:
                self._remote_misses += 1
                return None
            payload = json.loads(raw)
            self.local.set(key, payload, self.default_ttl_seconds)
            self._remote_hits += 1
            return payload
        except Exception as exc:
            self._remote_errors += 1
            trace_exception(
                logger,
                "generation_cache.remote_get.failed",
                exc,
                cache_key_fingerprint=key[:16],
            )
            return None

    def set(self, key: str, payload: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        self.local.set(key, payload, ttl)
        if self.remote is None:
            return
        try:
            self.remote.setex(key, json.dumps(payload, separators=(",", ":"), ensure_ascii=False), ttl)
        except Exception as exc:
            self._remote_errors += 1
            trace_exception(
                logger,
                "generation_cache.remote_set.failed",
                exc,
                cache_key_fingerprint=key[:16],
            )

    def delete(self, key: str) -> None:
        self.local.delete(key)
        if self.remote is None:
            return
        try:
            self.remote.delete(key)
        except Exception as exc:
            self._remote_errors += 1
            trace_exception(
                logger,
                "generation_cache.remote_delete.failed",
                exc,
                cache_key_fingerprint=key[:16],
            )

    def stats(self) -> dict[str, Any]:
        base = self.local.stats()
        base.update(
            {
                "backend": "upstash+local" if self.remote else "local",
                "remote_hits": self._remote_hits,
                "remote_misses": self._remote_misses,
                "remote_errors": self._remote_errors,
            }
        )
        return base


def build_generation_cache(
    *,
    max_entries: int,
    default_ttl_seconds: int,
    upstash_url: str = "",
    upstash_token: str = "",
) -> GenerationCache:
    local = TTLGenerationCache(max_entries=max_entries, default_ttl_seconds=default_ttl_seconds)
    if upstash_url and upstash_token:
        remote = UpstashRedisClient(base_url=upstash_url, token=upstash_token)
        return HybridGenerationCache(
            local_cache=local,
            remote=remote,
            default_ttl_seconds=default_ttl_seconds,
        )
    return HybridGenerationCache(local_cache=local, remote=None, default_ttl_seconds=default_ttl_seconds)
