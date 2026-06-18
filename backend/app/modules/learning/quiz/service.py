"""Compatibility re-export — prefer `learning.quiz.application.service`."""

from backend.app.modules.learning.quiz.application.service import QuizService, get_quiz_service

__all__ = ["QuizService", "get_quiz_service"]
