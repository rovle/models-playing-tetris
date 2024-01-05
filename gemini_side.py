"""
Actions that Gemini will be able to do:
    - Left ("left")
    - Right ("right")
    - Down ("down")
    - Complete down ("drop")
    - Rotate clockwise ("turn right")
    - Rotate counterclockwise ("turn left")
"""
import os
import shutil
import time
import subprocess
import google.generativeai as genai
from google.api_core.exceptions import InternalServerError
import PIL.Image
from dotenv import load_dotenv
import argparse
from datetime import datetime
import json
import pdb

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--manual", help="manual mode", action="store_true")
args = parser.parse_args()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro-vision")
TEMPERATURE = 0.4 # we could eventually get this via argumentparser, as well
                    # as the model and such things :catthinking4K:
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def generate_ai_response(prompt_name, example_ids, image_path):
    with open("assets/prompts.json", "r") as prompt_file:
        prompts = json.load(prompt_file)
    with open("assets/examples.json", "r") as example_file:
        examples = json.load(example_file)

    prompt = prompts.get(prompt_name, {})
    instructions = prompt.get("instructions", None)
    tetrominoes_color = prompt.get("tetrominoes_color", None)
    agumentation = prompt.get("agumentation", None)

    example_responses = []
    example_imgs = []
    for example in examples:
        if example["id"] in example_ids:
            example_responses.append(
                {
                    "board_state": example["board_state"],
                    "tetromino": example["tetromino"],
                    "explanation": example["explanation"],
                    "action": example["action"],
                }
            )
            example_imgs.append(PIL.Image.open(example["image_path"]))

    example_responses = [json.dumps(example) for example in example_responses]

    example_images_and_responses = []
    for pair in zip(example_imgs, example_responses):
        for img_response in pair:
            example_images_and_responses.append(img_response)

    current_board_img = PIL.Image.open(image_path)

    response = model.generate_content(
        contents=[
            instructions,
            *example_images_and_responses,
            current_board_img,
        ],
        generation_config=genai.types.GenerationConfig(
            temperature=TEMPERATURE,
        ),
        stream=False,
    )

    return response.text


def parse_ai_response(response_text):
    print(response_text, "\n")
    stripped_text = response_text[
        response_text.index("{") : (response_text.index("}") + 1)
    ]
    json = eval(stripped_text)

    responses_path = f"responses/responses_{current_time}.txt"
    with open(responses_path, "a") as fp:
        fp.write(stripped_text)
        fp.write("\n\n")

    return json["action"]


def get_user_input():
    response = input("Just for testing, tell me... ")
    return response


def get_gemini_response(prompt_name, example_ids, image_path=None):
    if args.manual:
        return get_user_input()

    retry_count = 0
    while retry_count < 50:
        try:
            response_text = generate_ai_response(prompt_name, example_ids, image_path)
            break
        except InternalServerError:
            retry_count += 1
            print(f"Internal server error {retry_count}/50, retrying...")
            time.sleep(1)
            continue

    if retry_count == 50:
        print("Failed to get a response after 50 retries.")
        exit()

    action = parse_ai_response(response_text)
    return action


def refresh_folders():
    if os.path.exists("screens"):
        shutil.rmtree("screens")
    os.mkdir("screens")

    if os.path.exists("actions"):
        shutil.rmtree("actions")
    os.mkdir("actions")

    if os.path.exists("responses"):
        shutil.rmtree("responses")
    os.mkdir("responses")


def create_video(game_number):
    command = [
        "nohup",
        "ffmpeg",
        "-framerate",
        "2",
        "-i",
        "screens/screenshot_%d.png",
        "-c:v",
        "libx264",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        f"game_{game_number}.mp4",
    ]

    # Start the subprocess without waiting for it to finish
    with (
        open("ffmpeg_output.log", "w") as output_log,
        open("ffmpeg_error.log", "w") as error_log,
    ):
        subprocess.Popen(
            command,
            cwd=f"previous_games/game_{game_number}",
            stdout=output_log,
            stderr=error_log,
        )


def main():
    # read the folder previous_games and get the last game number
    # then start from last game number + 1
    # if there is no previous_games folder, start from 1
    folder_names = os.listdir("previous_games")
    game_number = 1 + max([int(folder.split("_")[1]) for folder in folder_names])

    refresh_folders()

    with open("new_game.txt", "w") as fp:
        fp.write("0")

    with open("finished_restart.txt", "w") as fp:
        fp.write("0")

    state_counter = 1

    prompt_name = input(
        "Please start the game. Then enter the name of the prompt you want to use: "
    )
    example_ids = input(
        "Enter the IDs of the examples you want to use separated by commas: "
    )
    example_ids = example_ids.split(",")
    example_ids = [example_id.strip() for example_id in example_ids]

    while True:
        time.sleep(1)
        image_path = f"screens/screenshot_{state_counter-1}.png"
        action = get_gemini_response(prompt_name, example_ids, image_path=image_path)
        with open(f"actions/action_{state_counter}", "w") as fp:
            fp.write(action)
        while True:
            time.sleep(0.1)
            with open("new_game.txt", "r") as fp:
                new_game = fp.read().split(",")
            if new_game[0] == str(state_counter):
                break
        state_counter += 1
        if new_game[1] == "1":
            # move actions, screens and responses folders to game_number folder
            os.mkdir(f"previous_games/game_{game_number}")
            shutil.move("actions", f"previous_games/game_{game_number}/actions")
            shutil.move("screens", f"previous_games/game_{game_number}/screens")
            shutil.move("responses", f"previous_games/game_{game_number}/responses")
            with open("pieces_count.txt", "r") as fp:
                pieces_count = int(fp.read())

            information_dict = {
                "prompt_name": prompt_name,
                "example_ids": [int(x) for x in example_ids],
                "pieces_count": pieces_count,
                "model" : "gemini-pro-vision", # for now ...
                "temperature": TEMPERATURE
            }
            # save as json in game_number folder
            with open(f"previous_games/game_{game_number}/info.json", "w") as fp:
                json.dump(information_dict, fp)

            refresh_folders()
            create_video(game_number)
            state_counter = 1
            game_number += 1

            with open("new_game.txt", "w") as fp:
                fp.write("0,0")
            with open("finished_restart.txt", "w") as fp:
                fp.write("1")


if __name__ == "__main__":
    main()
