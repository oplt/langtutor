from __future__ import annotations

from fastapi import FastAPI

from backend.app.modules.ai.api import router as ai_router
from backend.app.modules.auth.api import router as auth_router
from backend.app.modules.book.api import router as book_router
from backend.app.modules.learning.api import router as learning_router
from backend.app.modules.learning.path_api import router as learning_path_router
from backend.app.modules.learning.quiz_api import router as learning_quiz_router
from backend.app.modules.knowledge.api import router as knowledge_router
from backend.app.modules.memory.api import router as memory_router
from backend.app.modules.privacy.api import router as privacy_router
from backend.app.modules.prompt.api import router as prompts_router
from backend.app.modules.settings.api import router as settings_router
from backend.app.modules.tutor.api import router as tutor_router
from backend.app.modules.tutor.ws import router as tutor_ws_router
from backend.app.modules.tutor.sessions.api import router as tutor_sessions_router
from backend.app.modules.notebook.api import router as notebook_router
from backend.app.modules.persona.api import router as personas_router
from backend.app.modules.skills.api import router as skills_router
from backend.app.modules.extensions.api import router as extensions_router
from backend.app.modules.rag.api.routes import router as rag_router
from backend.app.modules.rag.api.ws import router as rag_ws_router
from backend.app.modules.reading.api import router as reading_router


def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(privacy_router)
    app.include_router(learning_router)
    app.include_router(learning_path_router)
    app.include_router(learning_quiz_router)
    app.include_router(book_router)
    app.include_router(knowledge_router)
    app.include_router(skills_router)
    app.include_router(personas_router)
    app.include_router(notebook_router)
    app.include_router(memory_router)
    app.include_router(settings_router)
    app.include_router(ai_router)
    app.include_router(prompts_router)
    app.include_router(tutor_router)
    app.include_router(tutor_ws_router)
    app.include_router(tutor_sessions_router)
    app.include_router(extensions_router)
    app.include_router(rag_router)
    app.include_router(rag_ws_router)
    app.include_router(reading_router)
