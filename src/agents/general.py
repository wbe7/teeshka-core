"""General Agent implementation (Phase 11).

Handles general queries (chit-chat, world knowledge) that do not require tool usage.
Acts as a fallback "chat" agent.
"""

from src.agents.base import AgentResult, BaseAgent, SessionProtocol
from src.agents.dependencies import LLMClient
from src.api.langfuse_client import get_prompt
from src.api.settings import Settings


class GeneralAgent(BaseAgent):
    """General Agent for chit-chat and simple questions.

    Uses a faster/cheaper model user-configured in Settings.
    """

    name = "general"

    def __init__(self, llm_client: LLMClient, settings: Settings) -> None:
        """Initialize General Agent.

        Args:
            llm_client: Shared LLM client instance
            settings: Configuration settings (for model selection)
        """
        self.llm_client = llm_client
        self.settings = settings

    async def run(
        self,
        _session: SessionProtocol | None,  # General agent might not need session
        query: str,
        _context: dict,
    ) -> AgentResult:
        """Process query using General LLM model.

        Args:
            session: User session (unused for now)
            query: User's question
            context: Additional context
        """
        # Simple system prompt for personality
        default_system = (
            "You are Teeshka, a helpful, intelligent, and concise AI assistant. "
            "You live in a Kubernetes cluster server but act as a friendly companion. "
            "Answer users questions clearly and briefly."
        )

        system_prompt = default_system
        langfuse_prompt = await get_prompt("general.system.v1")
        if langfuse_prompt:
            # Assuming text prompt without variables for system
            system_prompt = langfuse_prompt.compile()

        response_text = await self.llm_client.complete(
            prompt=query,
            system=system_prompt,
            model=self.settings.llm_model_general,  # Use configured general model
        )

        return AgentResult(text=response_text)
