import os
import json
from datetime import datetime
from lib.game_agent_comms import CommunicationsLog


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
    communications_log = CommunicationsLog()
    information_dict = {
        "tetris_seed": communications_log["tetris_seed"],
        "model": args.model,
        "temperature": args.temperature,
        "prompt_name": args.prompt_name,
        "example_ids": args.example_ids,
        "pieces_count": int(communications_log["pieces_count"]),
        "lines_cleared": int(communications_log["lines_cleared"]),
        "score": int(communications_log["score"]),
        "n_lines": communications_log["n_lines"],
        "t_spins": communications_log["t_spins"],
        "combo": int(communications_log["combo"]),
    }
    with open(f"games_archive/game_{game_number}/info.json", "w") as fp:
        json.dump(information_dict, fp)
