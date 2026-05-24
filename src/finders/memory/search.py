"""Memory search pipeline for finders."""
import time
from datetime import datetime
from finders.memory.database import MemoryDatabase
from finders.memory.types import MemorySearchResult
from finders.memory.store import MemoryStore, DAILY_FILE_RE, LONG_TERM_FILE


def _parse_date_from_filename(filename: str) -> datetime | None:
    """从文件名解析日期。"""
    try:
        date_str = filename.replace(".md", "")
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def _time_decay_score(base_score: float, file_date: datetime | None, half_life_days: float = 30) -> float:
    """应用时间衰减到搜索分数。"""
    if not file_date:
        return base_score

    days_old = (datetime.now() - file_date).days
    decay = 0.5 ** (days_old / half_life_days)
    return base_score * decay


def _mmr_deduplicate(results: list[MemorySearchResult], k: int, lam: float = 0.7) -> list[MemorySearchResult]:
    """MMR 去重，平衡相关性和多样性。"""
    if len(results) <= k:
        return results

    selected = []
    remaining = list(results)

    # First result: highest score
    selected.append(remaining.pop(0))

    while len(selected) < k and remaining:
        best = None
        best_mmr = -1

        for r in remaining:
            relevance = r.score
            # Simple diversity: penalize results from same file
            max_sim = max(
                (1.0 if r.path == s.path else 0.0)
                for s in selected
            ) if selected else 0
            mmr = lam * relevance - (1 - lam) * max_sim

            if mmr > best_mmr:
                best_mmr = mmr
                best = r

        if best:
            selected.append(best)
            remaining.remove(best)

    return selected


def search_memory(
    query: str,
    database: MemoryDatabase,
    store: MemoryStore,
    max_results: int = 6,
    min_score: float = 0.1,
    half_life_days: float = 30,
    mmr_lambda: float = 0.7,
) -> list[MemorySearchResult]:
    """完整的 Memory 搜索 pipeline。

    1. 关键词搜索（FTS5）
    2. 时间衰减
    3. MMR 去重
    """
    # Step 1: Keyword search
    raw_results = database.search_keyword(query, k=max_results * 3)

    if not raw_results:
        return []

    # Step 2: Enrich with file date for time decay
    enriched = []
    for r in raw_results:
        chunk = database.get_chunk(r["chunk_id"])
        if not chunk:
            continue

        # Parse date from filename
        file_date = _parse_date_from_filename(chunk.path)

        # Apply time decay
        decayed_score = _time_decay_score(r["score"], file_date, half_life_days)

        if decayed_score >= min_score:
            chunk.score = decayed_score
            enriched.append(chunk)

    # Sort by score descending
    enriched.sort(key=lambda x: x.score, reverse=True)

    # Step 3: MMR deduplication
    return _mmr_deduplicate(enriched, max_results, mmr_lambda)
