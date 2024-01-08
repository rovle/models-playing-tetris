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
import pdb
import argparse
import json
from dotenv import load_dotenv
from datetime import datetime
import google.generativeai as genai
from google.api_core.exceptions import InternalServerError
from PIL import Image
import image_transformation as img_transform
import base64
import requests


load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--manual", help="manual mode", action="store_true")
parser.add_argument(
    "--model", help="model name for AI generation", default="gemini-pro-vision"
)
parser.add_argument(
    "--temperature", type=float, help="temperature for AI generation", default=0.4
)
parser.add_argument(
    "--prompt_name", help="name of the prompt for AI generation", default="prompt_1"
)
parser.add_argument(
    "--example_ids",
    type=int,
    nargs="*",
    help="list of IDs of examples to use",
    default=[],
)
args = parser.parse_args()

with open("assets/prompts.json", "r") as prompt_file:
    prompts = json.load(prompt_file)
with open("assets/examples.json", "r") as example_file:
    examples = json.load(example_file)

if args.model == "gemini-pro-vision":
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel(args.model)

if (
    args.model == "gpt-4-vision-preview"
):  # TODO check whether this is still the name (it is in the docs)
    api_key = os.environ.get("OPENAI_API_KEY")
    model = "gpt-4-vision-preview"


def generate_gemini_response(prompt_name, example_ids, image_path):
    prompt = prompts.get(prompt_name, {})
    instructions = prompt.get("instructions", None)
    augmentation = prompt.get("augmentation", None)

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
            example_imgs.append(Image.open(example["image_path"]))

    example_responses = [json.dumps(example) for example in example_responses]

    example_images_and_responses = []
    for pair in zip(example_imgs, example_responses):
        example_images_and_responses.extend(pair)

    current_board_img = Image.open(image_path)
    if augmentation:
        current_board_imgs = img_transform.apply_augmentations(
            image_path, augmentation
        ) + [current_board_img]
    else:
        current_board_imgs = [current_board_img]

    response = model.generate_content(
        contents=[
            instructions,
            *example_images_and_responses,
            *current_board_imgs,
        ],
        generation_config=genai.types.GenerationConfig(
            temperature=args.temperature,
        ),
        stream=False,
    )

    return response.text


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def generate_gpt4v_response(prompt_name, example_ids, image_path):
    prompt = prompts.get(prompt_name, {})
    instructions = prompt.get("instructions", None)
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
            example_imgs.append(encode_image(example["image_path"]))

    example_responses = [json.dumps(example) for example in example_responses]

    example_images_and_responses = []
    for img, response in zip(example_imgs, example_responses):
        example_images_and_responses.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}
        )
        example_images_and_responses.append({"type": "text", "text": response})

    current_board_img = encode_image(image_path)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    print(example_images_and_responses)
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "system",
                "content": "You are `gpt-4-vision-preview`, the latest OpenAI model that can describe images provided by the user in extreme detail. The user has attached an image to this message for you to analyse, there is MOST DEFINITELY an image attached, you will never reply saying that you cannot see the image because the image is absolutely and always attached to this message. Always give a sequence of actions, separated by commas and ending with drop.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instructions},
                    # *example_images_and_responses,
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{current_board_img}"
                        },
                    },
                ],
            },
        ],
        "max_tokens": 3000,
        "temperature": args.temperature,
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )

    response = response.json()
    response_text = response["choices"][0]["message"]["content"]

    return response_text


def parse_ai_response(response_text):
    print(response_text, "\n")
    stripped_text = response_text[
        response_text.index("{") : (response_text.index("}") + 1)
    ]
    json = eval(stripped_text)

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    responses_path = f"responses/responses_{current_time}.txt"
    with open(responses_path, "a") as fp:
        fp.write(stripped_text)
        fp.write("\n\n")

    action = json.get("action", None) or json.get("actions", None)
    if "," in action:
        action = action.split(",")
        # strip spaces
        action = [action.strip() for action in action]
    else:
        action = [action]
    return action


def get_user_input():
    response = input("Enter your next move: ")
    return response


def get_ai_response(prompt_name, example_ids, image_path=None):
    if args.manual:
        return get_user_input()

    retry_count = 0
    while retry_count < 50:
        try:
            if args.model == "gemini-pro-vision":
                response_text = generate_gemini_response(
                    prompt_name, example_ids, image_path
                )
            if args.model == "gpt-4-vision-preview":
                response_text = generate_gpt4v_response(
                    prompt_name, example_ids, image_path
                )
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

    input("Start the game and then press Enter...")
    if args.manual:
        print(
            "The possible moves are: left, right, down, drop, turn right and turn left"
        )

    while True:
        time.sleep(1)
        image_path = f"screens/screenshot_{state_counter-1}.png"
        actions = get_ai_response(
            args.prompt_name, args.example_ids, image_path=image_path
        )
        for action in actions:
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
                    "prompt_name": args.prompt_name,
                    "example_ids": args.example_ids,
                    "pieces_count": pieces_count,
                    "model": args.model,
                    "temperature": args.temperature,
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
