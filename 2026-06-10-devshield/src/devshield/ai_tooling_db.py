"""Known AI tooling packages database.

These are the packages DevShield specifically monitors for supply chain attacks.
Grouped by ecosystem and vendor.
"""

# AI tooling packages by ecosystem
AI_TOOLING_PACKAGES: dict[str, list[str]] = {
    "npm": [
        # Anthropic
        "@anthropic-ai/claude-code",
        "@anthropic-ai/sdk",
        # OpenAI
        "openai",
        # Google
        "@google/generative-ai",
        "@google-ai/generativelanguage",
        # Microsoft / VS Code
        "@vscode/extension",
        "vscode",
        # Cursor
        "cursor",
        # General AI
        "langchain",
        "@langchain/core",
        "llamaindex",
        # Copilot
        "github-copilot",
    ],
    "pip": [
        # Anthropic
        "anthropic",
        # OpenAI
        "openai",
        # Google
        "google-generativeai",
        "google-cloud-aiplatform",
        # LangChain
        "langchain",
        "langchain-core",
        "langchain-community",
        "langchain-openai",
        "langchain-anthropic",
        # LlamaIndex
        "llama-index",
        # Hugging Face
        "huggingface-hub",
        "transformers",
        # General AI
        "dspy",
        "outlines",
    ],
}

# Flat set for fast lookup
ALL_AI_PACKAGES: set[str] = set()
for pkgs in AI_TOOLING_PACKAGES.values():
    ALL_AI_PACKAGES.update(pkgs)


def is_ai_tooling(package_name: str, ecosystem: str) -> bool:
    """Check if a package is a known AI tooling package."""
    pkgs = AI_TOOLING_PACKAGES.get(ecosystem, [])
    return package_name.lower() in {p.lower() for p in pkgs}


def get_ai_packages(ecosystem: str) -> list[str]:
    """Get all known AI tooling packages for an ecosystem."""
    return AI_TOOLING_PACKAGES.get(ecosystem, [])
