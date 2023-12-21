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
import google.generativeai as genai
import PIL.Image
from dotenv import load_dotenv
import argparse

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--manual", help="manual mode", action="store_true")
args = parser.parse_args()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


def get_gemini_response(image_path=None):
    if args.manual:
        response = input("Just for testing, tell me... ")
        return response

    prompt = 'Imagine you are a Tetris player with superhuman abilities. You have the power to see 5 moves ahead and can instantly calculate the best possible move for any given board state. You also have perfect hand-eye coordination and can execute any move with precision.\n\nYou will be given a series of screenshots, each representing a different board state in the game. For each screenshot, you should output an integer representing the best move to make. The possible moves are:\n\nLeft: 1\nRight: 2\nDown: 3\nDrop: 4\nRotate clockwise: 5\nRotate counterclockwise: 6\n\nThe board state is represented by a grid of 10 columns and 20 rows. Each cell in the grid can be empty or contain a Tetris block. The Tetris blocks are represented by different colors and are called tetraminoes. At the right of the screen, you can see the tetraminoes that will fall next.\n\nThe game starts with a random sequence of Tetris blocks falling from the top of the screen. You can move the falling block left or right, and also rotate it clockwise or counterclockwise. You can also drop the block immediately to the bottom.\n\nWhen a complete row of blocks is formed, it disappears and the blocks above it fall down. Points are scored for each row that is cleared. The game ends when the blocks reach the top of the screen.\n\nYour goal is to play Tetris and achieve the highest possible score by maximizing cleared lines and minimizing block gaps. It\'s important to prioritize moves that achieve the scoring objective first, then prioritize filling gaps, and lastly consider immediate dropping to keep the game flowing.\n\nStructure your response as a JSON, so as {"action" : NUMBER} where NUMBER is an integer representing the best move to make for each screenshot. Your response should start with { and end with }.'

    img = PIL.Image.open(image_path)
    model = genai.GenerativeModel("gemini-pro-vision")
    response = model.generate_content([prompt, img], stream=False)

    text = response.text
    print(f"Gemini response: {text}")
    stripped_text = text[text.index("{") : (text.index("}") + 1)]
    print(f"Stripped text: {stripped_text}")
    json = eval(stripped_text)
    action = json["action"]

    action_mapping = {
        1: "left",
        2: "right",
        3: "down",
        4: "drop",
        5: "turn right",
        6: "turn left",
    }
    action_text = action_mapping.get(action)
    print(f"Action: {action_text}")
    return action_text


state_counter = 1

if os.path.exists("screens"):
    files = os.listdir("screens")
    for file in files:
        if file != "screenshot_0.png":
            os.remove(os.path.join("screens", file))
else:
    os.mkdir("screens")

if os.path.exists("actions"):
    shutil.rmtree("actions")
os.mkdir("actions")

while True:
    time.sleep(1)
    image_path = f"screens/screenshot_{state_counter-1}.png"
    action = get_gemini_response(image_path=image_path)
    with open(f"actions/action_{state_counter}", "w") as fp:
        fp.write(action)
    state_counter += 1
