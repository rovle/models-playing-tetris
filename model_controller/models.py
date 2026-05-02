import sys
import io
import base64
import json
import random
from datetime import datetime

import litellm

litellm.suppress_debug_info = True
from dotenv import load_dotenv

import lib.image_transformation as img_transform
from lib.json_utils import extract_json_object
from lib.prompts import load_prompts

load_dotenv(override=True)

prompts = load_prompts("assets/prompts")
with open("assets/examples.json", "r") as example_file:
    examples = json.load(example_file)


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


def _ephemeral_text_block(text):
    return {
        "type": "text",
        "text": text,
        "cache_control": {"type": "ephemeral"},
    }


def _log_full_prompt(messages):
    """Print the assembled prompt. Reads as the actual prompt text;
    [image: ...] and [CACHE BREAKPOINT] are the only markers inserted by this logger."""

    lines = ["[PROMPT] ===== full prompt ====="]
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        lines.append(f"--- {role} ---")
        if isinstance(content, str):
            lines.append(content)
            continue
        for block in content:
            block_type = block.get("type", "unknown")
            if block_type == "text":
                text = block.get("text", "")
                if block.get("cache_control"):
                    text = text.rstrip("\n") + "\n[CACHE BREAKPOINT]"
                lines.append(text)
            elif block_type == "image_url":
                url = block.get("image_url", {}).get("url", "")
                if url.startswith("data:image"):
                    size = len(url) - url.index(",") - 1
                    lines.append(f"[image: base64 elided, {size} chars]")
                else:
                    lines.append(f"[image: {url}]")
            else:
                lines.append(f"[{block_type}]")
    lines.append("[PROMPT] ===== end =====")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def _legacy_analysis(example):
    """Assemble an analysis block from older example schemas that pre-date the
    explicit ``analysis`` field (e.g. ``board_state`` + ``move_analysis``)."""
    legacy_keys = (
        "board_state",
        "preliminary_analysis",
        "move_analysis",
        "final_analysis",
    )
    parts = [
        f"{key.replace('_', ' ').capitalize()}: {example[key]}"
        for key in legacy_keys
        if key in example
    ]
    return "\n".join(parts)


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
        self._prompt_logged = False

    def generate_response(self, prompt_name, example_ids, image_path):
        prompt = prompts.get(prompt_name, {})
        instructions = prompt.get("instructions", "")
        augmentation = prompt.get("augmentation")

        # Few-shot examples and the current board live in a single user message
        # with explicit XML wrapping so the model can distinguish demonstrations
        # (<example>...</example>) from the board it must act on
        # (<current_board>...</current_board>).
        content_blocks = []

        example_lookup = {ex["id"]: ex for ex in examples}
        matched_examples = [
            example_lookup[i] for i in example_ids if i in example_lookup
        ]

        for example in matched_examples:
            img_b64 = img_transform.encode_image(example["image_path"])
            output_dict = {
                "tetromino": example["tetromino"],
                "action": example["action"],
            }
            analysis = example.get("analysis") or _legacy_analysis(example)

            content_blocks.append({"type": "text", "text": "<example>\n<board_image>"})
            content_blocks.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                }
            )
            closing = "</board_image>\n"
            if analysis:
                closing += f"<analysis>\n{analysis}\n</analysis>\n"
            closing += f"<output>{json.dumps(output_dict)}</output>\n</example>\n"
            content_blocks.append({"type": "text", "text": closing})

        # Mark the cache breakpoint on the last example's closing text so the
        # provider can reuse the static prefix across moves. With no examples,
        # the breakpoint moves to the system message instead (handled below).
        if (
            _supports_explicit_cache_control(self.model_name)
            and content_blocks
            and content_blocks[-1]["type"] == "text"
        ):
            content_blocks[-1]["cache_control"] = {"type": "ephemeral"}

        # Current board image(s) (augmented variants + original), wrapped in <current_board>
        image_content = []
        if augmentation:
            for pil_img in img_transform.apply_augmentations(image_path, augmentation):
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                aug_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                image_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{aug_b64}"},
                    }
                )
        current_img_b64 = img_transform.encode_image(image_path)
        image_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{current_img_b64}"},
            }
        )

        content_blocks.append({"type": "text", "text": "\n<current_board>"})
        content_blocks.extend(image_content)
        content_blocks.append({"type": "text", "text": "</current_board>"})

        current_msg = {"role": "user", "content": content_blocks}

        if _supports_explicit_cache_control(self.model_name) and not matched_examples:
            system_message = {
                "role": "system",
                "content": [_ephemeral_text_block(instructions)],
            }
        else:
            system_message = {"role": "system", "content": instructions}

        messages = [system_message, current_msg]

        if not self._prompt_logged:
            _log_full_prompt(messages)
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

        response = litellm.completion(**completion_kwargs)

        message = response.choices[0].message
        reasoning = _extract_reasoning(message)
        if reasoning:
            print(f"[REASONING] {reasoning}")

        _log_cache_usage(getattr(response, "usage", None))

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


def get_model(model_name, temperature=0.4, extra_body=None, reasoning_effort=None):
    if model_name == "random":
        return RandomPlayer(model_name, temperature)
    if model_name == "manual":
        return ManualPlayer(model_name, temperature)
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
