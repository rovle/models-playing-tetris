import os
import time
import argparse
import json
from dotenv import load_dotenv
from datetime import datetime

from google.api_core.exceptions import InternalServerError

from video_creation import create_video
from game_agent_comms import (create_new_communications_log,
                              update_communications_log,
                              read_communications_log)
from models import get_model

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--model", help="model name for AI generation", default="gemini-pro-vision"
)
parser.add_argument(
    "--temperature", type=float, help="temperature for AI generation", default=0.4
)
parser.add_argument(
    "--prompt_name", help="name of the prompt for AI generation"
)
parser.add_argument(
    "--example_ids",
    type=int,
    nargs="*",
    help="list of IDs of examples to use",
    default=[],
)
args = parser.parse_args()

model = get_model(args.model, args.temperature)

def check_if_valid_json(response_text):
    try:
        stripped_text = response_text[
            response_text.index("{") : (response_text.index("}") + 1)
        ]
        json = eval(stripped_text)
        return True
    except:
        return False

def parse_response(response_text):
    print(response_text, "\n")
    stripped_text = response_text[
        response_text.index("{") : (response_text.index("}") + 1)
    ]
    json = eval(stripped_text)

    action = json.get("action", None) or json.get("actions", None)
    if "," in action:
        action = action.split(",")
        action = [action.strip() for action in action]
    else:
        action = [action]
    return action, stripped_text

def get_ai_response(prompt_name, example_ids, image_path=None):
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
        except InternalServerError:
            retry_count += 1
            print(f"Internal server error {retry_count}/50, retrying...")
            time.sleep(1)
            continue

    if retry_count == 50:
        print("Failed to get a response after 50 retries. :(")
        exit()

    action = parse_response(response_text)
    return action


def create_new_game_folder(num):
    os.mkdir(f"games_archive/game_{num}")
    for name in ['screens', 'actions', 'responses']:
        os.mkdir(f"games_archive/game_{num}/{name}")
    return None 

def main():
    if not os.path.exists("games_archive"):
        os.mkdir("games_archive")

    folder_names = os.listdir("games_archive")
    if len(folder_names) > 0:
        game_number = 1 + max( [int(folder.split("_")[1])
                               for folder in folder_names] )
    else:
        game_number = 1
       
    create_new_game_folder(game_number) 
    create_new_communications_log()
    
    state_counter = 1

    input("Start the game and then press Enter...")
    if args.model == "manual":
        print(
            "The possible moves are: left, right, down, drop, rotate clockwise and rotate counterclockwise."
        )
    while True:
        time.sleep(0.5)
        image_path = f"games_archive/game_{game_number}/screens/screenshot_{state_counter-1}.png"
        actions, detailed_response = get_ai_response(
            args.prompt_name, args.example_ids, image_path=image_path
        )

        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        responses_path = f"games_archive/game_{game_number}/responses/responses_{current_time}.txt"
        with open(responses_path, "w") as fp:
            fp.write(detailed_response)

        for action in actions:
            with open(f"games_archive/game_{game_number}/actions/action_{state_counter}", "w") as fp:
                fp.write(action)
            while True:
                time.sleep(0.1)
                if read_communications_log("state_counter") == str(state_counter):
                    break
            state_counter += 1
            if read_communications_log("game_over") == "1":
                information_dict = {
                    "prompt_name": args.prompt_name,
                    "example_ids": args.example_ids,
                    "pieces_count": int(read_communications_log("pieces_count")),
                    "model": args.model,
                    "temperature": args.temperature,
                }
                with open(f"games_archive/game_{game_number}/info.json", "w") as fp:
                    json.dump(information_dict, fp)

                create_video(game_number)
                state_counter = 1
                game_number += 1
                create_new_game_folder(game_number)
                update_communications_log("finished_restart", "1")
                update_communications_log("game_over", "0")


if __name__ == "__main__":
    main()