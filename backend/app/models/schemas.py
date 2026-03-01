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
    status: str = "ready"  # "processing" | "ready" | "error"
    error: str | None = None


class CharacterInfo(BaseModel):
    id: str
    name: str
    description: str | None = None
    example_quotes: list[str] = Field(default_factory=list)


class CharacterRelationship(BaseModel):
    source_id: str
    target_id: str
    source_name: str
    target_name: str
    relationship: str
    description: str | None = None


# --- Chat ---
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str = Field(..., max_length=10000)
    citations: list[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    book_id: str
    character_id: str
    message: str = Field(..., min_length=1, max_length=5000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    conversation_id: str | None = None


class ChatChunk(BaseModel):
    """Streamed chunk: either content delta or a citation."""
    type: str  # "content" | "citation" | "done"
    content: str = ""
    citation: dict | None = None


# --- Group Chat ---
class GroupChatRequest(BaseModel):
    book_id: str
    character_ids: list[str]
    message: str = Field(..., min_length=1, max_length=5000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=100)


class GroupChatMessage(ChatMessage):
    character_id: str = ""
    character_name: str = ""
