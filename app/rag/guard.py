"""Mavzudan tashqari so'rovlardan himoya (LLM'ga bormasdan oldin).

Qatlamlar (arzonidan qimmatiga):
 1. Raqam + pul/xarajat belgisi bor xabar -> o'tkaziladi.
 2. Embedding sozlangan bo'lsa: xabar knowledge/ chunklariga pgvector orqali solishtiriladi,
    o'xshashlik pastroq bo'lsa rad etiladi.
 3. Embedding yo'q bo'lsa: knowledge/ dagi so'zlar lug'ati bilan solishtiriladi.
Xabar rad etilsa Claude chaqirilmaydi, ya'ni token sarflanmaydi.
"""

import hashlib
import logging
import re
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.db.models import KnowledgeChunk
from app.rag.embeddings import VoyageEmbedder

log = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path("knowledge")
_WORD = re.compile(r"[a-zA-Zа-яА-ЯёЁʻ'’`oʼ]{3,}")
_MONEY_HINT = re.compile(
    r"\d.*(so'?m|sum|сум|ming|mln|million|k\b|uzs)|(so'?m|sum|сум|ming|mln|million|k\b|uzs).*\d",
    re.IGNORECASE,
)

REFUSAL = (
    "Men faqat shaxsiy moliya bo'yicha yordam beraman: xarajat yozish, budget va "
    "bo'limlar limitlarini boshqarish, statistika. Iltimos, shu mavzuda yozing."
)


def load_chunks() -> list[tuple[str, str]]:
    """knowledge/*.md fayllarini bo'sh qator bo'yicha bo'laklarga ajratadi."""
    chunks = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        for part in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
            part = part.strip()
            if len(part) > 20:
                chunks.append((path.name, part))
    return chunks


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text)}


class TopicGuard:
    def __init__(
        self,
        settings: Settings,
        sessions: async_sessionmaker,
        embedder: VoyageEmbedder | None,
    ):
        self._min_sim = settings.rag_min_similarity
        self._sessions = sessions
        self._embedder = embedder
        self._vocab: set[str] = set()

    async def index(self) -> None:
        chunks = load_chunks()
        for _, text in chunks:
            self._vocab |= _tokens(text)
        if self._embedder is None:
            log.warning("Embedding sozlanmagan: lug'at asosidagi mavzu filtri ishlatiladi")
            return
        hashed = {hashlib.sha256(t.encode()).hexdigest(): (src, t) for src, t in chunks}
        async with self._sessions() as s:
            existing = set(await s.scalars(select(KnowledgeChunk.content_hash)))
            stale = existing - hashed.keys()
            if stale:
                await s.execute(
                    delete(KnowledgeChunk).where(KnowledgeChunk.content_hash.in_(stale))
                )
            new = [(h, *hashed[h]) for h in hashed.keys() - existing]
            if new:
                vectors = await self._embedder.embed([t for _, _, t in new], is_query=False)
                s.add_all(
                    KnowledgeChunk(source=src, content_hash=h, content=t, embedding=v)
                    for (h, src, t), v in zip(new, vectors, strict=True)
                )
            await s.commit()
        log.info("RAG indeks: %d chunk (%d yangi)", len(hashed), len(new))

    async def is_on_topic(self, text: str) -> bool:
        if _MONEY_HINT.search(text):
            return True
        if self._embedder is None:
            return bool(_tokens(text) & self._vocab)
        try:
            [vec] = await self._embedder.embed([text], is_query=True)
        except Exception:
            log.exception("Embedding xatosi, lug'atga o'tildi")
            return bool(_tokens(text) & self._vocab)
        async with self._sessions() as s:
            dist = await s.scalar(
                select(KnowledgeChunk.embedding.cosine_distance(vec))
                .order_by(KnowledgeChunk.embedding.cosine_distance(vec))
                .limit(1)
            )
        return dist is not None and (1 - dist) >= self._min_sim
