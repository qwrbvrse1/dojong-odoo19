# -*- coding: utf-8 -*-
"""
Vector Cache — ormcache-backed caching for vector similarity results.

Caches:
- Recent query → top-K results (avoids redundant embedding + pgvector calls)
- Intent type → domain agent mapping (fast agent routing)

Cache is invalidated when intent schemas or embeddings change.
"""

import hashlib
import json
import logging
import time

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)

# LRU cache for recent queries — keyed by (query_hash, top_k, threshold)
_QUERY_CACHE_TTL = 1800  # 30 minutes


class AiVectorCache(models.AbstractModel):
    _name = "ai.vector.cache"
    _description = "Vector Query Cache"

    @api.model
    @tools.ormcache("query_hash", "top_k", "threshold")
    def _cached_find_similar(self, query_hash, top_k, threshold):
        """
        Cached wrapper around vector_store.find_similar().

        The cache key is (query_hash, top_k, threshold).
        Returns the raw result list.
        """
        raise NotImplementedError("Should not reach here — see find_similar_cached()")

    @api.model
    def find_similar_cached(self, query_text, top_k=5, threshold=0.7):
        """
        Find similar intents with caching.

        First checks LRU cache for a recent identical query.
        On miss, delegates to vector_store.find_similar() and caches the result.

        Args:
            query_text: User's natural language query.
            top_k: Max results.
            threshold: Min similarity score.

        Returns:
            list[dict]: Same format as vector_store.find_similar().
        """
        query_hash = hashlib.sha256(query_text.encode()).hexdigest()[:16]

        # Try the in-memory LRU cache
        cache_key = f"vector_query:{query_hash}:{top_k}:{threshold}"
        cached = self._get_lru_cache(cache_key)
        if cached is not None:
            _logger.debug("Vector cache HIT for query hash %s", query_hash)
            return cached

        # Cache miss — perform the actual vector search
        VectorStore = self.env["ai.vector.store"]
        results = VectorStore.find_similar(query_text, top_k=top_k, threshold=threshold)

        # Store in LRU cache
        self._set_lru_cache(cache_key, results)
        _logger.debug("Vector cache MISS for query hash %s — %d results cached", query_hash, len(results))
        return results

    # ─── Simple In-Memory LRU Cache ───────────────────────────────────────────

    _lru_store = {}
    _lru_max_size = 500

    @classmethod
    def _get_lru_cache(cls, key):
        """Get a value from the LRU cache if it exists and is not expired."""
        entry = cls._lru_store.get(key)
        if entry is None:
            return None
        if time.time() - entry["ts"] > _QUERY_CACHE_TTL:
            del cls._lru_store[key]
            return None
        return entry["val"]

    @classmethod
    def _set_lru_cache(cls, key, value):
        """Set a value in the LRU cache with current timestamp."""
        if len(cls._lru_store) >= cls._lru_max_size:
            oldest_keys = sorted(cls._lru_store, key=lambda k: cls._lru_store[k]["ts"])
            for k in oldest_keys[: len(oldest_keys) // 4]:
                del cls._lru_store[k]
        cls._lru_store[key] = {"val": value, "ts": time.time()}

    @classmethod
    def clear_query_cache(cls):
        """Clear all cached query results. Called when embeddings are rebuilt."""
        cls._lru_store.clear()
        _logger.info("Vector query cache cleared")

    # ─── Agent Routing Cache ──────────────────────────────────────────────────
    @api.model
    @tools.ormcache()
    def get_intent_agent_map(self):
        """
        Get a cached mapping of intent_type → domain_agent.

        Used for quick agent routing without a DB query.

        Returns:
            dict: {"attendance_checkin": "attendance", "member_enroll": "enrollment", ...}
        """
        cr = self.env.cr
        cr.execute(
            "SELECT intent_type, domain_agent FROM ai_vector_store "
            "WHERE domain_agent IS NOT NULL"
        )
        return {row[0]: row[1] for row in cr.fetchall()}

    @api.model
    def invalidate_all(self):
        """Invalidate all vector caches. Call after rebuild_embeddings()."""
        self.clear_query_cache()
        self.env.registry.clear_cache()
        _logger.info("All vector caches invalidated")
