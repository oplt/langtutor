"""rag_chunks embedding: JSONB -> pgvector with cosine HNSW index

Revision ID: 20240618_pgvector
Revises:
Create Date: 2024-06-18

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20240618_pgvector"
down_revision = None
branch_labels = None
depends_on = None

# Must match backend.app.core.config.Settings.RAG_EMBEDDING_DIMENSION default.
EMBEDDING_DIMENSION = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Portable JSONB arrays -> native vector type for database-side similarity search.
    op.execute(
        f"""
        ALTER TABLE rag_chunks
        ALTER COLUMN embedding TYPE vector({EMBEDDING_DIMENSION})
        USING (
            CASE
                WHEN embedding IS NULL THEN NULL
                ELSE (embedding::text)::vector
            END
        )
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_cosine_hnsw
        ON rag_chunks
        USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_embedding_cosine_hnsw")
    op.execute(
        """
        ALTER TABLE rag_chunks
        ALTER COLUMN embedding TYPE jsonb
        USING (
            CASE
                WHEN embedding IS NULL THEN NULL
                ELSE to_jsonb(embedding::text::json)
            END
        )
        """
    )
