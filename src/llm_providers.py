"""Groq chat model factory."""
from __future__ import annotations

from langchain_groq import ChatGroq

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def get_chat_model(api_key: str) -> ChatGroq:
    """Return a ChatGroq instance configured for the Sculptor."""
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=api_key,
        temperature=0.4,
    )
