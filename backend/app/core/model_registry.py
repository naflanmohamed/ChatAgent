from dataclasses import dataclass


@dataclass(frozen=True)
class ModelOption:
    id: str
    provider: str
    label: str
    description: str
    tier: str
    supports_tools: bool = True


MODEL_OPTIONS = (
    ModelOption(
        id="gemini-2.5-flash",
        provider="gemini",
        label="Gemini 2.5 Flash",
        description="Reliable default for reasoning, RAG, and tool use.",
        tier="balanced",
    ),
    ModelOption(
        id="gemini-2.5-flash-lite",
        provider="gemini",
        label="Gemini 2.5 Flash-Lite",
        description="Faster, lighter option for simple conversations and extraction.",
        tier="fast",
    ),
    ModelOption(
        id="gemini-2.5-pro",
        provider="gemini",
        label="Gemini 2.5 Pro",
        description="Deeper reasoning for difficult analysis and research tasks.",
        tier="pro",
    ),
    ModelOption(
        id="openai/gpt-oss-120b",
        provider="groq",
        label="Groq · GPT-OSS 120B",
        description="Fast high-capability model for advanced agentic work and tool use.",
        tier="pro",
    ),
    ModelOption(
        id="llama-3.1-8b-instant",
        provider="groq",
        label="Groq · Llama 3.1 8B",
        description="Very fast model for lightweight conversations and routine tasks.",
        tier="fast",
    ),
)

MODEL_MAP = {m.id: m for m in MODEL_OPTIONS}


def is_supported_model(model_id: str) -> bool:
    return model_id in MODEL_MAP


def get_model_option(model_id: str) -> ModelOption | None:
    return MODEL_MAP.get(model_id)


def get_model_options() -> list[dict]:
    return [
        {
            "id": m.id,
            "provider": m.provider,
            "label": m.label,
            "description": m.description,
            "tier": m.tier,
            "supports_tools": m.supports_tools,
        }
        for m in MODEL_OPTIONS
    ]
