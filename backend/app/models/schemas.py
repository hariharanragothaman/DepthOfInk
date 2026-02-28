"""Request/response schemas for the API."""
from pydantic import BaseModel, Field


# --- Book / PDF ---
class BookCreate(BaseModel):
    """After PDF upload, optional title override."""
    title: str | None = None


class BookInfo(BaseModel):
    id: str
    title: str
    character_ids: list[str] = Field(default_factory=list)


class CharacterInfo(BaseModel):
    id: str
    name: str
    description: str | None = None
    example_quotes: list[str] = Field(default_factory=list)


# --- Chat ---
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    citations: list[dict] = Field(default_factory=list)  # [{ "text", "page", "source" }]


class ChatRequest(BaseModel):
    book_id: str
    character_id: str
    message: str
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatChunk(BaseModel):
    """Streamed chunk: either content delta or a citation."""
    type: str  # "content" | "citation" | "done"
    content: str = ""
    citation: dict | None = None
