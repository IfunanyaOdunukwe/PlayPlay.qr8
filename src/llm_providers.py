"""LLM provider factory — returns a langchain BaseChatModel for the selected provider."""

PROVIDERS = [
    {"id": "openai", "label": "OpenAI (GPT-4o)", "needs_key": True},
    {"id": "google", "label": "Google Gemini", "needs_key": True},
    {"id": "ollama", "label": "Ollama (Local)", "needs_key": False},
]


def get_available_providers():
    return PROVIDERS


def get_chat_model(provider: str, api_key: str | None = None, model_name: str | None = None):
    """Return a langchain chat model for the given provider.

    Imports are lazy so only the selected provider's package needs to be installed.
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name or "gpt-4o",
            api_key=api_key,
            temperature=0.4,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-3.1-flash-lite-preview",
            google_api_key=api_key,
            temperature=0.4,
        )

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=model_name or "llama3",
            temperature=0.4,
        )

    raise ValueError(f"Unknown provider: {provider}")
