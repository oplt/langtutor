"""Import all SQLAlchemy models so Alembic can populate Base.metadata."""

from __future__ import annotations

from backend.app.modules.extensions.classroom.models import ClassroomGrant
from backend.app.modules.extensions.partners.models import PartnerChannel, PartnerMessageLog
from backend.app.modules.knowledge.models import KnowledgeBase, KnowledgeChunk
from backend.app.modules.learning.models import (
    UserLessonPageProgress,
    UserMasteryProgress,
    UserWordProgress,
    Word,
    WordForm,
)
from backend.app.modules.memory.models import UserMemoryDocument, UserMemoryTrace
from backend.app.modules.notebook.models import WordNotebookEntry
from backend.app.modules.rag.infrastructure.sqlalchemy_models import (
    RagChunk,
    RagDocument,
    RagIngestionJob,
    RagQueryLog,
)
from backend.app.modules.stories.models import Story, StoryWord
from backend.app.modules.tutor.sessions.models import TutorChatSession, TutorChatTurn
from backend.app.modules.users.models import User

__all__ = [
    "ClassroomGrant",
    "KnowledgeBase",
    "KnowledgeChunk",
    "PartnerChannel",
    "PartnerMessageLog",
    "RagChunk",
    "RagDocument",
    "RagIngestionJob",
    "RagQueryLog",
    "Story",
    "StoryWord",
    "TutorChatSession",
    "TutorChatTurn",
    "User",
    "UserLessonPageProgress",
    "UserMasteryProgress",
    "UserMemoryDocument",
    "UserMemoryTrace",
    "UserWordProgress",
    "Word",
    "WordForm",
    "WordNotebookEntry",
]
