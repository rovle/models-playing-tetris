"""Builds the prompt for a single move.

Runs are only comparable if every backend sends the same instructions, examples
and images, so the prompt is built once here and the adapters at the bottom
convert it to each backend's own format.

Blocks look like:
    {"type": "text", "text": str, "cache_breakpoint": bool}
    {"type": "image", "data": <base64 str>, "media_type": str}
"""

import base64
import io
import json
import mimetypes
import sys
from pathlib import Path

import lib.image_transformation as img_transform

DEFAULT_MEDIA_TYPE = "image/png"


def _media_type(path):
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed if guessed and guessed.startswith("image/") else DEFAULT_MEDIA_TYPE


def _image_block(path):
    return {
        "type": "image",
        "data": img_transform.encode_image(path),
        "media_type": _media_type(path),
    }


def _pil_image_block(pil_image):
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return {
        "type": "image",
        "data": base64.b64encode(buf.getvalue()).decode("utf-8"),
        "media_type": DEFAULT_MEDIA_TYPE,
    }


def _legacy_analysis(example):
    """Build the analysis text for older examples that have no ``analysis`` field."""
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


def build_request(prompt, examples, example_ids, image_path):
    """Return ``(instructions, blocks, has_examples)`` for one move.

    Examples and the current board share one user message, so the XML tags are
    what tell the model which board it has to play.
    """
    instructions = prompt.get("instructions", "")
    augmentation = prompt.get("augmentation")

    blocks = []

    example_lookup = {ex["id"]: ex for ex in examples}
    matched_examples = [example_lookup[i] for i in example_ids if i in example_lookup]

    for example in matched_examples:
        output_dict = {"tetromino": example["tetromino"], "action": example["action"]}
        analysis = example.get("analysis") or _legacy_analysis(example)

        blocks.append({"type": "text", "text": "<example>\n<board_image>"})
        blocks.append(_image_block(example["image_path"]))
        closing = "</board_image>\n"
        if analysis:
            closing += f"<analysis>\n{analysis}\n</analysis>\n"
        closing += f"<output>{json.dumps(output_dict)}</output>\n</example>\n"
        blocks.append({"type": "text", "text": closing})

    # Everything above stays the same between moves, so it is worth caching.
    # With no examples there is nothing to mark here and the adapters cache the
    # system message instead.
    if blocks and blocks[-1]["type"] == "text":
        blocks[-1]["cache_breakpoint"] = True

    blocks.append({"type": "text", "text": "\n<current_board>"})
    if augmentation:
        for pil_img in img_transform.apply_augmentations(image_path, augmentation):
            blocks.append(_pil_image_block(pil_img))
    blocks.append(_image_block(image_path))
    blocks.append({"type": "text", "text": "</current_board>"})

    return instructions, blocks, bool(matched_examples)


def to_openai_messages(instructions, blocks, has_examples, cache_control=False):
    """Convert to the OpenAI-style chat format litellm expects."""
    content = []
    for block in blocks:
        if block["type"] == "image":
            url = f"data:{block['media_type']};base64,{block['data']}"
            content.append({"type": "image_url", "image_url": {"url": url}})
            continue
        text_block = {"type": "text", "text": block["text"]}
        if cache_control and block.get("cache_breakpoint"):
            text_block["cache_control"] = {"type": "ephemeral"}
        content.append(text_block)

    if cache_control and not has_examples:
        system_content = [
            {
                "type": "text",
                "text": instructions,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    else:
        system_content = instructions

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": content},
    ]


def to_anthropic_content(blocks):
    """Convert to native Anthropic content blocks.

    No ``cache_control`` here: the Claude Code CLI adds its own, and a request
    is only allowed a few.
    """
    content = []
    for block in blocks:
        if block["type"] == "image":
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": block["media_type"],
                        "data": block["data"],
                    },
                }
            )
        else:
            content.append({"type": "text", "text": block["text"]})
    return content


def log_full_prompt(instructions, blocks):
    """Print the prompt as it will be sent. Only the [image: ...] and
    [CACHE BREAKPOINT] markers are added here; the rest is the real text."""
    lines = ["[PROMPT] ===== full prompt =====", "--- system ---", instructions, "--- user ---"]
    for block in blocks:
        if block["type"] == "image":
            lines.append(f"[image: base64 elided, {len(block['data'])} chars]")
            continue
        text = block["text"]
        if block.get("cache_breakpoint"):
            text = text.rstrip("\n") + "\n[CACHE BREAKPOINT]"
        lines.append(text)
    lines.append("[PROMPT] ===== end =====")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def load_examples(path="assets/examples.json"):
    with open(Path(path), "r") as example_file:
        return json.load(example_file)
