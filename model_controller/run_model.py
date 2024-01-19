import os
import time
from google.api_core.exceptions import InternalServerError

from lib.json_utils import check_if_valid_json
from lib.video_creation import create_video
from lib.game_agent_comms import CommunicationsLog
from model_controller.models import get_model, parse_response
from model_controller.game_archive_manager import (
    create_new_game_folder,
    save_detailed_response,
    save_action,
    save_info,
)


def get_model_response(model, prompt_name, example_ids, image_path=None):
    retry_count = 0
    while retry_count < 50:
        try:
            response_text = model.generate_response(
                prompt_name, example_ids, image_path
            )
            if check_if_valid_json(response_text):
                break
            else:
                retry_count += 1
                print(response_text)
                print(f"Invalid JSON {retry_count}/50, retrying...")
                continue
        except InternalServerError or KeyError:
            retry_count += 1
            print(f"Internal server error {retry_count}/50, retrying...")
            time.sleep(1)
            continue

    if retry_count == 50:
        print("Failed to get a response after 50 retries. :(")
        exit()

    action = parse_response(prompt_name, response_text)
    return action


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
    model = get_model(args.model, args.temperature)

    if not os.path.exists("games_archive"):
        os.mkdir("games_archive")

    game_number = get_next_game_number()
    create_new_game_folder(game_number)
    communications_log = CommunicationsLog(restart_log=True)
    if args.endless:
        communications_log["endless"] = True
    if args.tetris_seed:
        communications_log["tetris_seed"] = int(args.tetris_seed)
    state_counter = 1

    if args.model == "manual":
        print("The possible moves are: left, right, down, drop, rotate clockwise and rotate counterclockwise.")

    while True:
        image_path = f"games_archive/game_{game_number}/screens/screenshot_{state_counter-1}.png"
        while not os.path.exists(image_path):
            time.sleep(0.1)

        actions, detailed_response = get_model_response(
            model, args.prompt_name, args.example_ids, image_path=image_path
        )

        save_detailed_response(game_number, detailed_response)

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
