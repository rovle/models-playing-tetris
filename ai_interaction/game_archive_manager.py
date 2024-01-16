import os
import json
from datetime import datetime
from lib.game_agent_comms import read_communications_log


def create_new_game_folder(num):
    game_folder = f"games_archive/game_{num}"
    os.mkdir(game_folder)
    for name in ['screens', 'actions', 'responses']:
        os.mkdir(f"{game_folder}/{name}")

def save_detailed_response(game_number, detailed_response):
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    responses_path = f"games_archive/game_{game_number}/responses/response_{current_time}.txt"
    with open(responses_path, "w") as fp:
        fp.write(detailed_response)

def save_action(game_number, state_counter, action):
    with open(f"games_archive/game_{game_number}/actions/action_{state_counter}", "w") as fp:
        fp.write(action)

def save_info(game_number, args):
    information_dict = {
        "prompt_name": args.prompt_name,
        "example_ids": args.example_ids,
        "pieces_count": int(read_communications_log("pieces_count")),
        "model": args.model,
        "temperature": args.temperature,
    }
    with open(f"games_archive/game_{game_number}/info.json", "w") as fp:
        json.dump(information_dict, fp)
