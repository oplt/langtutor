from __future__ import annotations

from backend.app.modules.agent.chat.pipeline import ChatPipeline
from backend.app.modules.agent.capabilities.chat import ChatCapability
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus

SOLVE_TOOLS = ["ask_user", "rag"]

SOLVE_PROMPT = """
## Deep solve mode (grammar derivation)
Provide a rigorous, step-by-step grammatical analysis of the learner's Dutch sentence or question.
Structure every answer as:
1. **Restatement** — the target sentence or construction
2. **Constituents** — label phrases (NP, VP, etc.) in plain language
3. **Rule steps** — numbered derivation steps (word order, inflection, agreement)
4. **Common pitfalls** — one or two learner mistakes to avoid
5. **Mini drill** — one follow-up prompt for the learner

Use `rag` when you need conjugation tables or grammar references. Be explicit about assumptions.
""".strip()


class DeepSolveCapability(ChatCapability):
    name = "deep_solve"
    description = "Step-by-step Dutch grammar derivation and sentence analysis."

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        context.metadata["solve_mode"] = True
        if context.enabled_tools is None:
            context.enabled_tools = list(SOLVE_TOOLS)
        extra = str(context.metadata.get("extra_system_prompt") or "")
        context.metadata["extra_system_prompt"] = f"{extra}\n\n{SOLVE_PROMPT}".strip()
        pipeline = ChatPipeline(llm_task="tutor_chat", source="deep_solve")
        await pipeline.run(context, bus)
