import json
import random
import time
from datetime import datetime

import litellm

litellm.suppress_debug_info = True
from dotenv import load_dotenv

from lib.json_utils import extract_json_object
from lib.prompts import load_prompts
from model_controller.claude_code_model import CLAUDE_CODE_PREFIX, ClaudeCodeModel
from model_controller.prompt_builder import (
    build_request,
    load_examples,
    log_full_prompt,
    to_openai_messages,
)

load_dotenv(override=True)

prompts = load_prompts("assets/prompts")
examples = load_examples()


def _supports_explicit_cache_control(model_name):
    """Whether the model accepts ``cache_control: {"type": "ephemeral"}`` blocks.

    Gemini is excluded on purpose. Implicit caching on Gemini 2.5+ handles prefix reuse without our hint.
    """
    name = model_name.lower()
    direct_prefixes = (
        "anthropic/",
        "bedrock/anthropic.",
        "bedrock/claude",
        "vertex_ai/claude",
    )
    if name.startswith(direct_prefixes):
        return True
    if name.startswith("openrouter/"):
        upstream = name[len("openrouter/") :]
        return upstream.startswith("anthropic/") or "claude" in upstream
    return False


def _log_cache_usage(usage):
    """Print cache hit / write counts when present."""
    if usage is None:
        return
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) or 0
    created = getattr(usage, "cache_creation_input_tokens", 0) or 0
    if cached or created:
        print(f"[CACHE] read={cached} write={created}")


def _extract_reasoning(message):
    """Pull reasoning text from a litellm response message across providers.

    litellm normalizes most providers' thinking output to ``message.reasoning_content``
    (str). Anthropic additionally returns ``message.thinking_blocks`` (list of dicts
    with a ``thinking`` field). OpenRouter passthrough may use ``reasoning`` or
    ``reasoning_details`` as a last resort.
    """
    if reasoning := getattr(message, "reasoning_content", None):
        return reasoning

    blocks = getattr(message, "thinking_blocks", None) or []
    parts = [
        block.get("thinking", "")
        for block in blocks
        if isinstance(block, dict) and block.get("thinking")
    ]
    if parts:
        return "\n".join(parts)

    if reasoning := getattr(message, "reasoning", None):
        return reasoning
    if details := getattr(message, "reasoning_details", None):
        return str(details)
    return None


class LiteLLMModel:
    def __init__(
        self, model_name, temperature=0.4, extra_body=None, reasoning_effort=None
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.extra_body = extra_body or {}
        self.reasoning_effort = reasoning_effort
        self.last_metrics = {}
        self._prompt_logged = False

    def generate_response(self, prompt_name, example_ids, image_path):
        instructions, blocks, has_examples = build_request(
            prompts.get(prompt_name, {}), examples, example_ids, image_path
        )
        messages = to_openai_messages(
            instructions,
            blocks,
            has_examples,
            cache_control=_supports_explicit_cache_control(self.model_name),
        )

        if not self._prompt_logged:
            log_full_prompt(instructions, blocks)
            self._prompt_logged = True

        completion_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 16000,
            "num_retries": 10,
        }
        if self.extra_body:
            completion_kwargs["extra_body"] = self.extra_body
        if self.reasoning_effort:
            completion_kwargs["reasoning_effort"] = self.reasoning_effort

        started = time.monotonic()
        response = litellm.completion(**completion_kwargs)
        duration_ms = int((time.monotonic() - started) * 1000)

        message = response.choices[0].message
        reasoning = _extract_reasoning(message)
        if reasoning:
            print(f"[REASONING] {reasoning}")

        usage = getattr(response, "usage", None)
        _log_cache_usage(usage)
        self.last_metrics = {
            "backend": "litellm",
            "model": self.model_name,
            "duration_ms": duration_ms,
            "usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "total_cost_usd": getattr(response, "_hidden_params", {}).get(
                "response_cost"
            ),
        }

        return message.content, reasoning


class RandomPlayer:
    def __init__(self, model_name="random", temperature=0.4):
        self.model_name = model_name
        self.temperature = temperature

    def generate_response(self, prompt_name, example_ids, image_path):
        actions = ["left", "right", "down", "drop", "turn right", "turn left"]
        return f'{{"action": "{random.choice(actions)}" }}', None


class ManualPlayer:
    def __init__(self, model_name="manual", temperature=0.4):
        self.model_name = model_name
        self.temperature = temperature

    def generate_response(self, prompt_name, example_ids, image_path):
        return f'{{"action": "{input("Enter your next move: ")}" }}', None


def get_model(
    model_name, temperature=0.4, extra_body=None, reasoning_effort=None, effort=None
):
    if model_name == "random":
        return RandomPlayer(model_name, temperature)
    if model_name == "manual":
        return ManualPlayer(model_name, temperature)
    if model_name.startswith(CLAUDE_CODE_PREFIX):
        return ClaudeCodeModel(model_name, prompts=prompts, examples=examples, effort=effort)
    return LiteLLMModel(
        model_name,
        temperature,
        extra_body=extra_body,
        reasoning_effort=reasoning_effort,
    )


def parse_response(prompt_name, response_text):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}]", response_text, "\n")

    prompt = prompts.get(prompt_name, {})
    action_type = prompt.get("action_type", None)

    stripped_text = extract_json_object(response_text)
    data = json.loads(stripped_text)
    action = data.get("action", None)

    if "," in action:
        action_arr = action.split(",")
        stripped_action_arr = (
            [action_arr[0].strip()]
            if action_type == "single"
            else [a.strip() for a in action_arr]
        )
    else:
        stripped_action_arr = [action]

    if stripped_action_arr[-1] not in ["down", "drop"]:
        stripped_action_arr.append("down")
    return stripped_action_arr, stripped_text, data
