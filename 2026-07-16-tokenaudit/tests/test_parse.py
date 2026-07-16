from tokenaudit.parse import (
    parse_session_text,
    messages_from_claude_jsonl,
)
from fixtures import claude_line, assistant_text, tool_use_read, tool_result, generic_line


def _claude_text():
    return "\n".join([
        claude_line("user", {"input_tokens": 5000, "output_tokens": 0}, content=[{"type": "text", "text": "system"}]),
        claude_line("assistant", {"input_tokens": 2000, "output_tokens": 100}, model="claude-sonnet-4", content=tool_use_read("a.py")),
        claude_line("user", {"input_tokens": 3000, "output_tokens": 0}, content=tool_result("big result here")),
        claude_line("assistant", {"input_tokens": 500, "output_tokens": 50}, model="claude-sonnet-4", content=assistant_text("done")),
    ]) + "\n"


def test_parse_claude_agent_and_count():
    sess = parse_session_text(_claude_text())
    assert sess.agent == "claude-code"
    assert len(sess.messages) == 4


def test_parse_claude_tool_use_and_reads():
    sess = parse_session_text(_claude_text())
    a = sess.messages[1]
    assert a.has_tool_use is True
    assert a.file_reads == ("a.py",)
    assert a.model == "claude-sonnet-4"
    assert a.usage.input_tokens == 2000
    assert a.usage.output_tokens == 100


def test_parse_claude_tool_result_flag():
    sess = parse_session_text(_claude_text())
    assert sess.messages[2].has_tool_result is True


def test_parse_claude_usage_alias_generic():
    text = generic_line("user", 123, 45) + "\n" + generic_line("assistant", 67, 89, model="gpt-4o")
    msgs = messages_from_claude_jsonl(text)  # generic parser used indirectly
    # generic_line has no "message" -> claude parser yields 0; use generic path:
    from tokenaudit.parse import parse_session_text as pst
    sess = pst(text)
    assert sess.agent == "generic"
    assert sess.messages[0].usage.input_tokens == 123
    assert sess.messages[1].usage.output_tokens == 89


def test_parse_skips_blank_and_malformed():
    text = "\n\nnot json at all\n" + _claude_text()
    sess = parse_session_text(text)
    # only the 4 valid claude lines survive
    assert len(sess.messages) == 4


def test_parse_generic_prompt_completion_mapping():
    text = generic_line("user", 100, 0) + "\n" + generic_line("assistant", 200, 30, model="gpt-4o")
    sess = parse_session_text(text)
    assert sess.agent == "generic"
    assert sess.messages[0].usage.input_tokens == 100
    assert sess.messages[1].usage.output_tokens == 30
