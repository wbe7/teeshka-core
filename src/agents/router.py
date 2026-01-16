"""Router Agent implementation (GEMINI.md §5)."""

from src.agents.base import AgentResult, BaseAgent, SessionProtocol


class RouterAgent(BaseAgent):
    """Router Agent implementation.

    Phase 9: Echo response.
    Phase 11: LLM classification + delegation.
    """

    name = "router"

    async def run(
        self,
        session: SessionProtocol,  # noqa: ARG002
        query: str,
        context: dict,  # noqa: ARG002
    ) -> AgentResult:
        """Process query and return result.

        Phase 9: Simple echo response.
        Phase 11: Use LLM for intent classification and delegation.
        """
        return AgentResult(text=f"Echo: {query}")
