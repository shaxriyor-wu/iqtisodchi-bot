from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.db.base import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(200))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(get_settings().embedding_dim))
