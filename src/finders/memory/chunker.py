"""Memory chunker for finders."""
import hashlib
from finders.memory.types import MemoryChunk


def split_into_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """将文本按段落分割，返回 (start_line, end_line, content)。"""
    lines = text.split("\n")
    paragraphs = []
    start = 0

    for i, line in enumerate(lines):
        if line.strip() == "" and i > start:
            content = "\n".join(lines[start:i]).strip()
            if content:
                paragraphs.append((start + 1, i, content))
            start = i + 1

    # Last paragraph
    if start < len(lines):
        content = "\n".join(lines[start:]).strip()
        if content:
            paragraphs.append((start + 1, len(lines), content))

    return paragraphs


def chunk_memory_text(
    file_path: str,
    text: str,
    chunk_tokens: int = 400,
    overlap_tokens: int = 80,
) -> list[MemoryChunk]:
    """将 memory 文本分块。"""
    paragraphs = split_into_paragraphs(text)
    if not paragraphs:
        return []

    chunk_budget = chunk_tokens * 3  # ~3 chars/token
    overlap_budget = overlap_tokens * 3

    chunks = []
    start_idx = 0

    while start_idx < len(paragraphs):
        content = ""
        start_line = paragraphs[start_idx][0]
        end_line = paragraphs[start_idx][1]
        end_idx = start_idx

        while end_idx < len(paragraphs):
            candidate = paragraphs[end_idx]
            candidate_text = f"{content}\n\n{candidate[2]}" if content else candidate[2]
            if len(candidate_text) > chunk_budget and content:
                break
            content = candidate_text
            end_line = candidate[1]
            end_idx += 1
            if len(content) >= chunk_budget:
                break

        if not content:
            break

        chunks.append(
            MemoryChunk(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                content=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
            )
        )

        # Overlap: carry some paragraphs from previous chunk
        start_idx = max(start_idx + 1, end_idx - (overlap_budget // 50))

    return chunks
