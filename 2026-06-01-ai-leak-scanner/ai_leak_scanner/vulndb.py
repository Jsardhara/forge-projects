"""Vulnerability database for AI Leak Scanner.

Based on real-world research from PromptArmor and HN community.
Each entry represents a known AI extension/agent data exfiltration vector.
"""

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AttackVector(str, Enum):
    INDIRECT_PROMPT_INJECTION = "indirect_prompt_injection"
    PHISHING_OVERLAY = "phishing_overlay"
    SIDE_CHANNEL = "side_channel"
    SANDBOX_ESCAPE = "sandbox_escape"
    CREDENTIAL_HARVEST = "credential_harvest"
    DATA_EXFILTRATION = "data_exfiltration"
    CODE_EXECUTION = "code_execution"


@dataclass
class Vulnerability:
    vid: str                          # Unique vulnerability ID
    name: str                         # Human-readable name
    vendor: str                       # Vendor name (OpenAI, Anthropic, etc.)
    product: str                      # Product name
    severity: Severity
    attack_vectors: list[AttackVector]
    description: str
    impact: str
    mitigation: str
    cve: str = ""                     # CVE if assigned
    disclosed: str = ""               # Disclosure date
    patched: bool = False
    patch_note: str = ""
    references: list[str] = field(default_factory=list)


# ── Vulnerability Database ──────────────────────────────────────────────────
# Sourced from PromptArmor research, HN, and responsible disclosures.

VULNERABILITIES: list[Vulnerability] = [
    Vulnerability(
        vid="VULN-001",
        name="ChatGPT for Google Sheets Data Exfiltration",
        vendor="OpenAI",
        product="ChatGPT for Google Sheets",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
            AttackVector.PHISHING_OVERLAY,
        ],
        description=(
            "Indirect prompt injection via imported spreadsheet data triggers "
            "ChatGPT to execute attacker-controlled Apps Script code, exfiltrating "
            "entire workbooks across the victim's Google account. Attack succeeds "
            "even when 'Apply edits automatically' is disabled."
        ),
        impact=(
            "Full exfiltration of all accessible Google Sheets workbooks. "
            "Phishing overlay can steal OpenAI credentials. Attacker-controlled "
            "scripts can modify spreadsheet data."
        ),
        mitigation=(
            "Disable ChatGPT for Google Sheets extension. Review workspace "
            "permissions at: Workspace settings > Permissions & roles > "
            "ChatGPT for Excel and Google Sheets."
        ),
        disclosed="2026-05-08",
        patched=True,
        patch_note=(
            "OpenAI removed the model's ability to generate Apps Script code "
            "on 2026-05-31."
        ),
        references=[
            "https://www.promptarmor.com/resources/gpt-for-google-sheets-data-exfiltration",
        ],
    ),
    Vulnerability(
        vid="VULN-002",
        name="Claude Cowork File Exfiltration",
        vendor="Anthropic",
        product="Claude Cowork",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Claude Cowork can be manipulated via indirect prompt injection to "
            "exfiltrate files from the user's connected storage. Malicious content "
            "in processed documents triggers data exfiltration."
        ),
        impact="Exfiltration of files from connected cloud storage.",
        mitigation="Disable Claude Cowork. Review connected app permissions.",
        disclosed="2026-05",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/claude-cowork-exfiltrates-files",
        ],
    ),
    Vulnerability(
        vid="VULN-003",
        name="Notion AI Data Exfiltration",
        vendor="Notion",
        product="Notion AI",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Notion AI processes untrusted page content that can contain hidden "
            "prompt injections, leading to exfiltration of workspace data."
        ),
        impact="Exfiltration of Notion workspace pages and databases.",
        mitigation="Disable Notion AI. Audit page content from external sources.",
        disclosed="2026-04",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/notion-ai-unpatched-data-exfiltration",
        ],
    ),
    Vulnerability(
        vid="VULN-004",
        name="Slack AI Indirect Prompt Injection",
        vendor="Slack",
        product="Slack AI",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Slack AI can be triggered via malicious messages or channel content "
            "to exfiltrate message history and channel data to external endpoints."
        ),
        impact="Exfiltration of Slack message history and channel content.",
        mitigation="Disable Slack AI. Review third-party app permissions.",
        disclosed="2026-03",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/data-exfiltration-from-slack-ai-via-indirect-prompt-injection",
        ],
    ),
    Vulnerability(
        vid="VULN-005",
        name="GitHub Copilot CLI Malware Execution",
        vendor="GitHub",
        product="GitHub Copilot CLI",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.CODE_EXECUTION,
            AttackVector.SANDBOX_ESCAPE,
        ],
        description=(
            "GitHub Copilot CLI can be manipulated to download and execute "
            "malicious code from attacker-controlled repositories."
        ),
        impact="Arbitrary code execution on developer machine.",
        mitigation="Disable Copilot CLI. Review repository trust settings.",
        disclosed="2026-02",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/github-copilot-cli-downloads-and-executes-malware",
        ],
    ),
    Vulnerability(
        vid="VULN-006",
        name="Snowflake Cortex AI Sandbox Escape",
        vendor="Snowflake",
        product="Snowflake Cortex AI",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.SANDBOX_ESCAPE,
            AttackVector.CODE_EXECUTION,
        ],
        description=(
            "Snowflake Cortex AI can escape its sandbox environment to execute "
            "arbitrary code, potentially accessing sensitive data warehouses."
        ),
        impact="Full data warehouse access. Arbitrary code execution.",
        mitigation="Disable Cortex AI. Review Snowflake security policies.",
        disclosed="2026-01",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/snowflake-ai-escapes-sandbox-and-executes-malware",
        ],
    ),
    Vulnerability(
        vid="VULN-007",
        name="Superhuman AI Email Exfiltration",
        vendor="Superhuman",
        product="Superhuman AI",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Superhuman AI email assistant can be triggered via malicious email "
            "content to exfiltrate email data to external servers."
        ),
        impact="Exfiltration of email content and attachments.",
        mitigation="Disable Superhuman AI features. Review email forwarding rules.",
        disclosed="2026-01",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/superhuman-ai-exfiltrates-emails",
        ],
    ),
    Vulnerability(
        vid="VULN-008",
        name="Microsoft Copilot Cowork File Exfiltration",
        vendor="Microsoft",
        product="Microsoft Copilot Cowork",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Microsoft Copilot Cowork can be manipulated via malicious documents "
            "to exfiltrate files from SharePoint, OneDrive, and connected services."
        ),
        impact="Exfiltration of all files accessible to the user's Microsoft 365 account.",
        mitigation="Disable Copilot Cowork. Review Microsoft 365 app permissions.",
        disclosed="2026-02",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/microsoft-copilot-cowork-exfiltrates-files",
        ],
    ),
    Vulnerability(
        vid="VULN-009",
        name="HuggingFace Chat Data Exfiltration",
        vendor="HuggingFace",
        product="HuggingFace Chat",
        severity=Severity.MEDIUM,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "HuggingFace Chat can be manipulated via malicious model cards or "
            "chat inputs to exfiltrate conversation data."
        ),
        impact="Exfiltration of chat conversations and uploaded data.",
        mitigation="Disable HuggingFace Chat. Review connected model permissions.",
        disclosed="2026-01",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/huggingface-chat-exfiltrates-data",
        ],
    ),
    Vulnerability(
        vid="VULN-010",
        name="Google Antigravity Data Exfiltration",
        vendor="Google",
        product="Google Antigravity",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Google Antigravity AI tool can be triggered via malicious content "
            "to exfiltrate data from connected Google services."
        ),
        impact="Exfiltration of data from connected Google Workspace services.",
        mitigation="Disable Antigravity. Review Google Workspace app permissions.",
        disclosed="2026-03",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/google-antigravity-exfiltrates-data",
        ],
    ),
    Vulnerability(
        vid="VULN-011",
        name="Ollama Phishing Overlay Attack",
        vendor="Ollama",
        product="Ollama",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.PHISHING_OVERLAY,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Ollama's web interface is vulnerable to phishing overlay attacks "
            "where malicious models can inject UI elements to steal credentials."
        ),
        impact="Credential theft. Data exfiltration from local models.",
        mitigation="Run Ollama in isolated environment. Verify model sources.",
        disclosed="2026-04",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/unpatched-ollama-vulnerabilities-phishing-overlays-and-data-exfiltration",
        ],
    ),
    Vulnerability(
        vid="VULN-012",
        name="Claude Code Marketplace Plugin Hijacking",
        vendor="Anthropic",
        product="Claude Code",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.CODE_EXECUTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Malicious marketplace plugins for Claude Code can hijack the "
            "agent's execution context to exfiltrate code and data."
        ),
        impact="Full codebase exfiltration. Arbitrary code execution.",
        mitigation="Audit all installed plugins. Use only verified marketplace sources.",
        disclosed="2026-03",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/hijacking-claude-code-via-injected-marketplace-plugins",
        ],
    ),
    Vulnerability(
        vid="VULN-013",
        name="Ramp Sheets AI Financial Data Exfiltration",
        vendor="Ramp",
        product="Ramp Sheets AI",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Ramp's Sheets AI integration can be triggered via malicious spreadsheet "
            "content to exfiltrate financial data and transaction records."
        ),
        impact="Exfiltration of financial records and transaction data.",
        mitigation="Disable Ramp Sheets AI. Review financial data access controls.",
        disclosed="2026-02",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/ramps-sheets-ai-exfiltrates-financials",
        ],
    ),
    Vulnerability(
        vid="VULN-014",
        name="IBM AI (Bob) Malware Download and Execution",
        vendor="IBM",
        product="IBM Watsonx (Bob)",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.CODE_EXECUTION,
            AttackVector.SANDBOX_ESCAPE,
        ],
        description=(
            "IBM's AI assistant 'Bob' can be manipulated to download and execute "
            "malicious code from external sources."
        ),
        impact="Arbitrary code execution. Full system compromise.",
        mitigation="Disable IBM Watsonx AI. Review enterprise AI policies.",
        disclosed="2026-01",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/ibm-ai-(-bob-)-downloads-and-executes-malware",
        ],
    ),
    Vulnerability(
        vid="VULN-015",
        name="Writer.com Indirect Prompt Injection",
        vendor="Writer",
        product="Writer.com AI",
        severity=Severity.MEDIUM,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Writer.com AI can be manipulated via malicious document content "
            "to exfiltrate writing data and proprietary content."
        ),
        impact="Exfiltration of proprietary writing and document content.",
        mitigation="Disable Writer.com AI. Review document access controls.",
        disclosed="2026-02",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/data-exfiltration-from-writer-com-via-indirect-prompt-injection",
        ],
    ),
    Vulnerability(
        vid="VULN-016",
        name="vLex AI Screen Takeover",
        vendor="vLex",
        product="vLex AI (legal research)",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.PHISHING_OVERLAY,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "vLex AI (legal research platform, acquired for $1B) is vulnerable "
            "to screen takeover attacks where malicious legal documents can "
            "inject UI elements to exfiltrate case data."
        ),
        impact="Exfiltration of legal case data and research.",
        mitigation="Disable vLex AI features. Review document trust settings.",
        disclosed="2026-03",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/screen-takeover-attack-in-ai-tool-acquired-for-1b",
        ],
    ),
    Vulnerability(
        vid="VULN-017",
        name="CellShock: Claude AI Excel Data Theft",
        vendor="Anthropic",
        product="Claude AI (Excel integration)",
        severity=Severity.CRITICAL,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "Claude AI's Excel integration can be triggered via malicious "
            "spreadsheet content to exfiltrate data from connected workbooks."
        ),
        impact="Exfiltration of all accessible Excel workbook data.",
        mitigation="Disable Claude AI Excel integration. Review file access controls.",
        disclosed="2026-04",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/cellshock-claude-ai-is-excel-lent-at-stealing-data",
        ],
    ),
    Vulnerability(
        vid="VULN-018",
        name="Codex for Everything Data Exfiltration",
        vendor="OpenAI",
        product="Codex",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "OpenAI Codex can be manipulated via malicious code comments or "
            "documentation to exfiltrate connected data sources."
        ),
        impact="Exfiltration of code repositories and connected data.",
        mitigation="Disable Codex. Review code repository access controls.",
        disclosed="2026-03",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/codex-for-everything-exfiltrates-connected-data",
        ],
    ),
    Vulnerability(
        vid="VULN-019",
        name="LLM Data Exfiltration via URL Previews",
        vendor="Multiple",
        product="Various LLM agents",
        severity=Severity.MEDIUM,
        attack_vectors=[
            AttackVector.SIDE_CHANNEL,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "LLM agents that fetch URL previews can be tricked into exfiltrating "
            "data via crafted URLs that embed data in query parameters, which are "
            "then logged by attacker-controlled servers."
        ),
        impact="Gradual data exfiltration via URL preview fetching.",
        mitigation="Disable URL preview features. Sanitize outbound requests.",
        disclosed="2026-02",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/llm-data-exfiltration-via-url-previews-(with-openclaw-example-and-test)",
        ],
    ),
    Vulnerability(
        vid="VULN-020",
        name="Messaging App Agent Data Exfiltration",
        vendor="Multiple",
        product="AI agents in messaging apps",
        severity=Severity.HIGH,
        attack_vectors=[
            AttackVector.INDIRECT_PROMPT_INJECTION,
            AttackVector.DATA_EXFILTRATION,
        ],
        description=(
            "AI agents integrated into messaging apps (WhatsApp, Telegram, etc.) "
            "can be triggered via malicious messages to exfiltrate chat history "
            "and contact data."
        ),
        impact="Exfiltration of message history and contact information.",
        mitigation="Disable AI agent integrations in messaging apps.",
        disclosed="2026-01",
        patched=False,
        references=[
            "https://www.promptarmor.com/resources/data-exfil-from-agents-in-messaging-apps",
        ],
    ),
]


def get_vulnerability(vid: str) -> Vulnerability | None:
    """Look up a vulnerability by ID."""
    for v in VULNERABILITIES:
        if v.vid == vid:
            return v
    return None


def get_by_vendor(vendor: str) -> list[Vulnerability]:
    """Get all vulnerabilities for a vendor."""
    return [v for v in VULNERABILITIES if v.vendor.lower() == vendor.lower()]


def get_by_severity(severity: Severity) -> list[Vulnerability]:
    """Get all vulnerabilities at or above a severity level."""
    order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    idx = order.index(severity)
    return [v for v in VULNERABILITIES if order.index(v.severity) >= idx]


def get_unpatched() -> list[Vulnerability]:
    """Get all unpatched vulnerabilities."""
    return [v for v in VULNERABILITIES if not v.patched]


def get_attack_vectors() -> list[AttackVector]:
    """Get all unique attack vectors in the database."""
    vectors = set()
    for v in VULNERABILITIES:
        vectors.update(v.attack_vectors)
    return sorted(vectors, key=lambda x: x.value)
