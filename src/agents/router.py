"""Router Agent implementation (GEMINI.md §5)."""

from src.agents.base import AgentResult, BaseAgent, SessionProtocol
from src.agents.dependencies import LLMClient
from src.agents.general import GeneralAgent
from src.agents.prompts import DEFAULT_ROUTER_PROMPT, RouterCategory
from src.api.langfuse_client import get_prompt
from src.api.settings import Settings
from src.llm.client import LLMError


class RouterAgent(BaseAgent):
    """Router Agent implementation.

    Phase 9: Echo response.
    Phase 11: LLM classification + delegation.
    """

    name = "router"

    def __init__(
        self,
        llm_client: LLMClient,
        settings: Settings,
        general_agent: GeneralAgent,
    ) -> None:
        """Initialize Router Agent.

        Args:
            llm_client: Specific LLM client for classification.
            settings: App configuration.
            general_agent: Initialized GeneralAgent for delegation.
        """
        self.llm_client = llm_client
        self.settings = settings
        self.general_agent = general_agent

    async def _classify_intent(self, query: str) -> str:
        """Classify user query into a category using LLM."""

        # Try to fetch prompt from Langfuse
        langfuse_prompt = await get_prompt("router.classification.v1")
        if langfuse_prompt:
            prompt = langfuse_prompt.compile(query=query)
        else:
            prompt = DEFAULT_ROUTER_PROMPT.format(query=query)

        response = await self.llm_client.complete(
            prompt=prompt,
            model=self.settings.llm_model_router,  # Use smart model for routing
        )
        # Parse logic: match first word to category
        category = response.strip().upper().split()[0]
        # Remove punctuation if present (e.g. "SRE.")
        category = category.rstrip(".,!?:;")

        # Verify it's a valid category
        if category in RouterCategory.__members__:
            return category

        return RouterCategory.UNKNOWN

    async def run(
        self,
        session: SessionProtocol | None,
        query: str,
        context: dict,
    ) -> AgentResult:
        """Process query: classify and delegate."""
        try:
            category = await self._classify_intent(query)
        except LLMError as e:
            # Fallback on LLM failure
            return AgentResult(text=f"I'm having trouble understanding you right now. Error: {e}")

        if category == RouterCategory.GENERAL:
            # Delegate to General Agent
            return await self.general_agent.run(session, query, context)

        if category == RouterCategory.UNKNOWN:
            return AgentResult(
                text="I'm sorry, I didn't understand that request. Could you clarify?"
            )

        # Stub delegation for other categories (Phase 11)
        return AgentResult(text=f"Routed to {category}: {query}")
