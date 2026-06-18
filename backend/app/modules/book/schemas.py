from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.app.modules.book.models import BlockStatus, BlockType, LessonBlock, LessonBook, LessonPage


class LessonBlockOut(BaseModel):
    id: str
    type: BlockType
    status: BlockStatus
    title: str
    params: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_block(cls, block: LessonBlock) -> "LessonBlockOut":
        return cls(
            id=block.id,
            type=block.type,
            status=block.status,
            title=block.title,
            params=block.params,
            payload=block.payload,
        )


class LessonPageOut(BaseModel):
    id: str
    book_id: str
    level: str
    chapter_id: str
    title: str
    grammar_topic: str
    learning_objectives: list[str]
    blocks: list[LessonBlockOut]

    @classmethod
    def from_page(cls, page: LessonPage) -> "LessonPageOut":
        return cls(
            id=page.id,
            book_id=page.book_id,
            level=page.level,
            chapter_id=page.chapter_id,
            title=page.title,
            grammar_topic=page.grammar_topic,
            learning_objectives=page.learning_objectives,
            blocks=[LessonBlockOut.from_block(block) for block in page.blocks],
        )


class LessonBookOut(BaseModel):
    id: str
    level: str
    title: str
    description: str
    chapters: list[dict[str, Any]]

    @classmethod
    def from_book(cls, book: LessonBook) -> "LessonBookOut":
        return cls(
            id=book.id,
            level=book.level,
            title=book.title,
            description=book.description,
            chapters=[
                {
                    "id": chapter.id,
                    "title": chapter.title,
                    "order": chapter.order,
                    "pages": [
                        {
                            "id": page.id,
                            "title": page.title,
                            "order": page.order,
                            "grammar_topic": page.grammar_topic,
                        }
                        for page in chapter.pages
                    ],
                }
                for chapter in book.chapters
            ],
        )


class LessonCompleteIn(BaseModel):
    quiz_score: float | None = None
