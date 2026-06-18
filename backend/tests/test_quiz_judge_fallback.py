import asyncio
from unittest.mock import AsyncMock, patch

from backend.app.modules.learning.quiz.llm import judge_with_llm


def test_judge_with_llm_short_circuits_exact_match() -> None:
    async def _run() -> None:
        with patch("backend.app.modules.learning.quiz.llm.get_llm_service") as llm_factory:
            result = await judge_with_llm(
                prompt="What is hello in Dutch?",
                question_type="short",
                correct_answer="hallo",
                explanation="",
                user_answer="Hallo",
                options=[],
                language="en",
            )
            llm_factory.assert_not_called()
            assert result["correct"] is True
            assert result["verdict"] == "correct"

    asyncio.run(_run())


def test_judge_with_llm_calls_llm_for_open_questions() -> None:
    async def _run() -> None:
        llm = AsyncMock()

        async def _stream(*args, **kwargs):
            yield "✅ Correct — good sentence."

        llm.stream = _stream
        with patch("backend.app.modules.learning.quiz.llm.get_llm_service", return_value=llm):
            result = await judge_with_llm(
                prompt="Write a sentence using 'fiets'.",
                question_type="open",
                correct_answer="Ik heb een fiets.",
                explanation="",
                user_answer="Ik rijd op mijn fiets.",
                options=[],
                language="en",
            )
            assert result["verdict"] in {"correct", "partial", "incorrect"}

    asyncio.run(_run())
