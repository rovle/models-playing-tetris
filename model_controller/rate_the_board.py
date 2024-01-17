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
import lib.image_transformation as img_transform
import base64
import requests
import random

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--model", help="model to test",
)
args = parser.parse_args()

considered_games = [30]

path = "previous_games"

paths_to_images = []

models = dict()
for game_num in considered_games:
    for filename in os.listdir(f"{path}/game_{game_num}/screens"):
        if int(filename.split("_")[1].split(".")[0]) >= 20:
            paths_to_images.append(f"{path}/game_{game_num}/{filename}")
    with open(f"{path}/game_{game_num}/info.json", "r") as fp:
        info = json.load(fp)
        models[game_num] = info['model']

if args.model == "gemini-pro-vision":
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel(args.model)

if (
    args.model == "gpt-4-vision-preview"
): 
    api_key = os.environ.get("OPENAI_API_KEY")
    model = "gpt-4-vision-preview"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


prompt_template="You will be shown the board of a Tetris game being played by {MODEL} before any lines have been cleared. Judge their performance based on the configuration of the board. Assign a numerical grade from 1 to 10, where 1 indicates a player not watching the screen, and 10 represents a Tetris master. Structure your response in JSON format as {\"grade\": INTEGER}, where INTEGER is the grade you assign."

def query_model(model_name, prompt, game_num, screen_num):
    if model_name == "gemini-pro-vision":
        image = Image.open(f"previous_games/game_{game_num}/screens/screenshot_{screen_num}.png")
        response = model.generate_content(
            contents=[
                prompt,
                image
            ],
            generation_config=genai.types.GenerationConfig(
                temperature=0,
            ),
            stream=False,
        )
    if model_name == "gpt-4-vision-preview":
        image = encode_image(f"previous_games/game_{game_num}/screens/screenshot_{screen_num}.png")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    # *example_images_and_responses,
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image}"
                        },
                    },
                ],
            },
        ],
        "max_tokens": 100,
        "temperature": 0,
        }
        response = response.json()
        response = response["choices"][0]["message"]["content"]
    stripped_text = response[
        response.index("{") : (response.index("}") + 1)
    ]
    json = eval(stripped_text)

    grade = json["grade"]
    
    return grade
    
        
for model_description in ["Gemini Pro Vision, a model trained by Google,",
                          "GPT-4 Vision, a model trained by OpenAI,",
                          "an elementary school student",
                          "a college student"]:
    grade = query_model(model_name=args.model,
                        prompt=prompt_template.format(MODEL=model_description),
                        game_num=30,
                        screen_num=20)
     


print(paths_to_images)
print(models)