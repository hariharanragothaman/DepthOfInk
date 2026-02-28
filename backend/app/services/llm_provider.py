"""LLM provider abstraction: swap between OpenAI, AWS Bedrock, or Ollama via config."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Generator

from app.config import settings


class LLMProvider(ABC):
    """Unified interface for chat completions and embeddings."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
    ) -> str:
        """Return assistant message content."""

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
    ) -> Generator[str | None, None, None]:
        """Yield content deltas, then None to signal end."""

    @abstractmethod
    def embed(self, text: str, model: str) -> list[float]:
        """Return embedding vector for a single text."""

    @abstractmethod
    def embed_batch(self, texts: list[str], model: str) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""


# ---------------------------------------------------------------------------
# OpenAI (also works for Ollama and any OpenAI-compatible API)
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        from openai import OpenAI
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    def chat(self, messages, model, temperature=0.7) -> str:
        r = self._client.chat.completions.create(
            model=model, messages=messages, temperature=temperature,
        )
        return (r.choices[0].message.content or "").strip()

    def chat_stream(self, messages, model, temperature=0.7):
        stream = self._client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        yield None

    def embed(self, text, model) -> list[float]:
        r = self._client.embeddings.create(model=model, input=text[:8000])
        return r.data[0].embedding

    def embed_batch(self, texts, model) -> list[list[float]]:
        out: list[list[float]] = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            r = self._client.embeddings.create(model=model, input=batch)
            out.extend(d.embedding for d in r.data)
        return out


# ---------------------------------------------------------------------------
# AWS Bedrock
# ---------------------------------------------------------------------------

class BedrockProvider(LLMProvider):
    """AWS Bedrock via boto3 (converse API for chat, invoke for embeddings)."""

    def __init__(self) -> None:
        import boto3
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
        )

    def chat(self, messages, model, temperature=0.7) -> str:
        system_blocks, converse_msgs = _split_bedrock_messages(messages)
        kwargs: dict[str, Any] = {
            "modelId": model,
            "messages": converse_msgs,
            "inferenceConfig": {"temperature": temperature, "maxTokens": 2048},
        }
        if system_blocks:
            kwargs["system"] = system_blocks
        r = self._client.converse(**kwargs)
        return r["output"]["message"]["content"][0]["text"]

    def chat_stream(self, messages, model, temperature=0.7):
        system_blocks, converse_msgs = _split_bedrock_messages(messages)
        kwargs: dict[str, Any] = {
            "modelId": model,
            "messages": converse_msgs,
            "inferenceConfig": {"temperature": temperature, "maxTokens": 2048},
        }
        if system_blocks:
            kwargs["system"] = system_blocks
        r = self._client.converse_stream(**kwargs)
        for event in r["stream"]:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                text = delta.get("text")
                if text:
                    yield text
        yield None

    def embed(self, text, model) -> list[float]:
        body = json.dumps({"inputText": text[:8000]})
        r = self._client.invoke_model(modelId=model, body=body)
        result = json.loads(r["body"].read())
        return result["embedding"]

    def embed_batch(self, texts, model) -> list[list[float]]:
        return [self.embed(t, model) for t in texts]


def _split_bedrock_messages(
    messages: list[dict[str, str]],
) -> tuple[list[dict], list[dict]]:
    """
    Bedrock converse API takes system as a separate param.
    Convert OpenAI-style messages to Bedrock format.
    """
    system_blocks: list[dict] = []
    converse_msgs: list[dict] = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            system_blocks.append({"text": content})
        else:
            converse_msgs.append({
                "role": role,
                "content": [{"text": content}],
            })
    return system_blocks, converse_msgs


# ---------------------------------------------------------------------------
# Provider factory (singleton)
# ---------------------------------------------------------------------------

_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Return the configured LLM provider (cached singleton)."""
    global _provider
    if _provider is not None:
        return _provider

    name = settings.llm_provider.lower()
    if name == "openai":
        _provider = OpenAIProvider()
    elif name == "bedrock":
        _provider = BedrockProvider()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
            "Supported: openai, bedrock"
        )
    return _provider
