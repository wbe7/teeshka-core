from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message structure."""

    content: str


class Choice(BaseModel):
    """Single completion choice."""

    message: Message


class CompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    choices: list[Choice] = Field(min_length=1)
