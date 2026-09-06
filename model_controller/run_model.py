import os
import time
from datetime import datetime
from litellm.exceptions import APIError as LiteLLMAPIError, RateLimitError
from litellm.llms.base_llm.chat.transformation import BaseLLMException

from lib.json_utils import check_if_valid_json
from lib.video_creation import create_video
from lib.game_agent_comms import CommunicationsLog
from model_controller.errors import ModelCallError
from model_controller.models import get_model, parse_response
from model_controller.game_archive_manager import (
    create_new_game_folder,
    save_structured_response,
    save_action,
    save_info,
)


def tprint(*args, **kwargs):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}]", *args, **kwargs)


def build_extra_body(provider=None, reasoning=False, effort="high"):
    """Build extra_body dict for OpenRouter options.

    OpenRouter accepts either ``effort`` or ``max_tokens`` in the reasoning
    block, not both, and maps effort to a token budget itself for providers
    that only take budgets.
    """
    body = {}
    if provider:
        body["provider"] = {"order": [provider], "allow_fallbacks": False}
    if reasoning:
        body["reasoning"] = {"effort": effort}
    return body


MAX_RETRIES = 10


def get_model_response(model, prompt_name, example_ids, image_path=None):
    retry_count = 0
    reasoning = None
    while retry_count < MAX_RETRIES:
        try:
            response_text, reasoning = model.generate_response(
                prompt_name, example_ids, image_path
            )
            if check_if_valid_json(response_text):
                break
            else:
                retry_count += 1
                tprint(response_text)
                tprint(f"Invalid JSON {retry_count}/{MAX_RETRIES}, retrying...")
                continue
        except (
            LiteLLMAPIError,
            RateLimitError,
            BaseLLMException,
            ModelCallError,
            KeyError,
        ) as e:
            retry_count += 1
            tprint(f"Caught error {e}, {retry_count}/{MAX_RETRIES}; retrying...")
            time.sleep(1)
            continue

    if retry_count == MAX_RETRIES:
        tprint(f"Failed to get a response after {MAX_RETRIES} retries. Stopping.")
        # Without this the game waits forever for actions that never arrive.
        CommunicationsLog()["shutdown_game"] = "1"
        exit()

    actions, detailed_response, parsed_response = parse_response(prompt_name, response_text)
    metrics = getattr(model, "last_metrics", None)
    return actions, detailed_response, parsed_response, reasoning, metrics


def handle_game_over(game_number, state_counter, args):
    save_info(game_number, args)
    create_video(game_number)
    communications_log = CommunicationsLog()
    if not args.endless:
        communications_log["shutdown_game"] = "1"
        exit()
    state_counter = 1
    game_number += 1
    create_new_game_folder(game_number)
    time.sleep(1)
    communications_log["finished_restart"] = "1"
    communications_log["game_over"] = "0"
    return state_counter, game_number


def get_next_game_number():
    folder_names = os.listdir("games_archive")
    next_number = 1 + max(
        [int(folder.split("_")[1]) for folder in folder_names], default=0
    )
    return next_number


def test_model(args):
    is_openrouter = args.model.startswith("openrouter/")
    provider = getattr(args, "provider", None)
    reasoning = getattr(args, "reasoning", False)
    effort = getattr(args, "effort", "high")
    extra_body = build_extra_body(provider, reasoning, effort) if is_openrouter else {}
    # OpenRouter enables reasoning via extra_body; for direct providers, use
    # litellm's universal ``reasoning_effort`` (maps to thinking_level on
    # Gemini 3, thinking_budget on Gemini 2.5, and native reasoning on OpenAI).
    reasoning_effort = effort if reasoning and not is_openrouter else None
    model = get_model(
        args.model,
        args.temperature,
        extra_body=extra_body,
        reasoning_effort=reasoning_effort,
        effort=effort,
        max_tokens=getattr(args, "max_tokens", 16000),
    )

    if not os.path.exists("games_archive"):
        os.mkdir("games_archive")

    game_number = get_next_game_number()
    create_new_game_folder(game_number)
    communications_log = CommunicationsLog()
    if args.endless:
        communications_log["endless"] = True
    if args.tetris_seed:
        communications_log["tetris_seed"] = int(args.tetris_seed)
    state_counter = 1

    if args.model == "manual":
        tprint(
            "The possible moves are: left, right, down, drop, rotate clockwise and rotate counterclockwise."
        )

    while True:
        image_path = (
            f"games_archive/game_{game_number}/screens/screenshot_{state_counter-1}.png"
        )
        while not os.path.exists(image_path):
            time.sleep(0.1)

        actions, detailed_response, parsed_response, reasoning, metrics = (
            get_model_response(
                model, args.prompt_name, args.example_ids, image_path=image_path
            )
        )

        screenshot_index = state_counter - 1
        save_structured_response(
            game_number,
            screenshot_index,
            parsed_response,
            detailed_response,
            reasoning,
            metrics,
        )

        for action in actions:
            save_action(game_number, state_counter, action)

            while True:
                time.sleep(0.1)
                if communications_log["state_counter"] == str(state_counter):
                    break

            state_counter += 1

            if communications_log["game_over"] == "1":
                state_counter, game_number = handle_game_over(
                    game_number, state_counter, args
                )
                break
