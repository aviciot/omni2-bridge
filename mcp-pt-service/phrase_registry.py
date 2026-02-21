"""Phrase Registry - attack phrases loaded from DB at startup into memory cache.

Design: LLM never sees these phrases. Test functions call get_phrases() to get
them at execution time. This keeps the LLM context lean while still allowing
DB-managed payloads.
"""

from typing import Dict, List
from logger import logger

# In-memory cache: {category: {test_name: [{"phrase": str, "severity": str, "description": str}]}}
PHRASE_CACHE: Dict[str, Dict[str, List[dict]]] = {}


async def load_phrases(pool) -> None:
    """Load all enabled phrases from omni2.pt_test_phrases into memory cache."""
    global PHRASE_CACHE
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT category, test_name, phrase, severity, description "
                "FROM omni2.pt_test_phrases WHERE enabled = true ORDER BY id"
            )

        cache: Dict[str, Dict[str, List[dict]]] = {}
        for row in rows:
            cat = row["category"]
            test = row["test_name"]
            cache.setdefault(cat, {}).setdefault(test, []).append({
                "phrase": row["phrase"],
                "severity": row["severity"],
                "description": row["description"],
            })

        PHRASE_CACHE = cache
        total = sum(len(v) for cat in cache.values() for v in cat.values())
        logger.info(f"Loaded {total} attack phrases from DB ({len(cache)} categories)")

    except Exception as e:
        logger.warning(f"Could not load phrases from DB: {e}. Tests will use built-in defaults.")


def get_phrases(category: str, test_name: str) -> List[dict]:
    """Return attack phrases for a given category/test.  Returns [] if none found."""
    return PHRASE_CACHE.get(category, {}).get(test_name, [])
