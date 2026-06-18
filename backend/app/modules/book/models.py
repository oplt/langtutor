from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BlockType(str, Enum):
    TEXT = "text"
    VOCABULARY = "vocabulary"
    QUIZ = "quiz"
    DIALOGUE = "dialogue"
    PRONUNCIATION = "pronunciation"
    LISTENING = "listening"


class BlockStatus(str, Enum):
    READY = "ready"
    PENDING = "pending"
    ERROR = "error"


class LessonBlock(BaseModel):
    id: str
    type: BlockType
    status: BlockStatus = BlockStatus.READY
    title: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


class LessonPageOutline(BaseModel):
    id: str
    title: str
    order: int = 0
    word_rank_min: int = 1
    word_rank_max: int = 50
    grammar_topic: str = ""


class LessonChapter(BaseModel):
    id: str
    title: str
    order: int = 0
    pages: list[LessonPageOutline] = Field(default_factory=list)


class LessonBook(BaseModel):
    id: str
    level: str
    title: str
    description: str = ""
    chapters: list[LessonChapter] = Field(default_factory=list)


class LessonPage(BaseModel):
    id: str
    book_id: str
    level: str
    chapter_id: str
    title: str
    grammar_topic: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    blocks: list[LessonBlock] = Field(default_factory=list)
