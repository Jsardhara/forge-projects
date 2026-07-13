"""Shared sample texts for contentmark tests (bare-module import).

Fixtures are deliberately contrasting so the detector has something to separate:
- HUMAN_TEXT: rambling, varied sentence lengths, few discourse connectors,
  no enumeration, specific low-frequency vocabulary.
- AI_TEXT: uniform ~10-word sentences, heavy connector phrases, numbered
  enumeration, repetitive high-frequency vocabulary.
"""
import re

# A rambling, naturally varied human voice. Should read HUMAN.
HUMAN_TEXT = (
    "So I went to the store. Big mistake. "
    "The line was out the door and honestly I just wanted milk. "
    "My kid kept tugging my sleeve, asking about dinosaurs for some reason. "
    "We left with crackers instead. Whatever. Tomorrow's problem, not mine. "
    "The cat judging me from the windowsill the whole time did not help."
)

# A flat, uniform, heavily-signposted machine-style passage. Should read AI.
AI_TEXT = (
    "Artificial intelligence is transforming the modern workplace in profound ways. "
    "Moreover, automation improves efficiency across many teams and departments. "
    "Furthermore, it reduces long-term costs for most organizations over time. "
    "Additionally, it enhances the quality of data-driven decision-making overall. "
    "First, companies should leverage automation to improve core workflows. "
    "Second, they must train employees to use these new tools effectively. "
    "Third, they should monitor outcomes to ensure consistent quality. "
    "Finally, human oversight remains a crucial and important safeguard. "
    "In conclusion, organizations must adopt these tools carefully and deliberately."
)

# Short text (<40 words) — must never be accused.
SHORT_TEXT = (
    "The cat sat on the warm windowsill and watched the rain. "
    "She seemed content, for a while."
)

# Plain text with no markers (for watermark negative tests).
PLAIN_TEXT = (
    "The quarterly report shows steady growth in the eastern region. "
    "Margins improved despite higher input costs and tighter staffing."
)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))
