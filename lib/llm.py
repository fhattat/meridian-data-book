# lib/llm.py
import json

def ask_llm(messages, tools=None):
    """The adapter from Chapter 15: calls your assistant's API and returns the reply as text."""
    raise NotImplementedError("connect ask_llm to your own assistant")

def ask_text(prompt, system=""):
    return ask_llm([{"role": "system", "content": system},
                    {"role": "user", "content": prompt}])

def ask_json(prompt, system=""):
    return json.loads(ask_text(prompt + "\nReply with JSON only.", system))

# ---------------------------------------------------------------------------------------------
# repo: an OPTIONAL ready-made adapter. The book leaves ask_llm() empty on purpose (Chapter 15):
# you connect your own assistant. If you set MERIDIAN_LLM=anthropic and install the `anthropic`
# package (pip install anthropic, ANTHROPIC_API_KEY in the environment), this adapter is used.
# MERIDIAN_LLM=scripted replays answers from a JSON file (Chapter 16.3 ScriptedLLM idea), for tests.
import os as _os

if _os.environ.get("MERIDIAN_LLM") == "anthropic":
    def ask_llm(messages, tools=None):  # noqa: F811
        import anthropic
        client = anthropic.Anthropic()
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        chat = [m for m in messages if m["role"] != "system"]
        reply = client.messages.create(model=_os.environ.get("MERIDIAN_LLM_MODEL", "claude-sonnet-5-5"),
                                       max_tokens=2000, system=system, messages=chat)
        return "".join(b.text for b in reply.content if getattr(b, "type", "") == "text")

elif _os.environ.get("MERIDIAN_LLM") == "scripted":
    _SCRIPT = iter(json.loads(open(_os.environ["MERIDIAN_LLM_SCRIPT"], encoding="utf-8").read()))

    def ask_llm(messages, tools=None):  # noqa: F811
        return next(_SCRIPT)
