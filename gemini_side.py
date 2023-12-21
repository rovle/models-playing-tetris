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
model = genai.GenerativeModel("gemini-pro-vision")


def get_gemini_response(image_path=None):
    if args.manual:
        response = input("Just for testing, tell me... ")
        return response

    prompt = 'Imagine you are a Tetris player with superhuman abilities. You have the power to see 5 moves ahead and can instantly calculate the best possible move for any given board state. You also have perfect hand-eye coordination and can execute any move with precision.\n\nI am presenting you with an image of a Tetris board at its current state. The board is represented by a grid of 10 columns and 10 rows. The empty cells are grey while the Tetrominoes are represented by red color. The possible moves are:\n\nLeft: "left"\nRight: "right"\nDown: "down"\nDrop: "drop"\nRotate clockwise: "turn right"5\nRotate counterclockwise: "turn left"\n\nThe game starts with a random Tetromino falling from the top of the board. You can move the falling Tetromino left or right, and also rotate it clockwise or counterclockwise. You can also drop the Tetromino immediately to the bottom.\n\nWhen a complete row of blocks is formed, it disappears and the blocks above it fall down. Points are scored for each row that is cleared. The game ends when the blocks reach the top of the board.\n\nYour goal is to play Tetris and achieve the highest possible score by maximizing cleared lines and minimizing block gaps. Let\'s think step by step:\n1. Analyze the board, the position of the current blocks and where the current tetromino would best slot in.\n2. Rank the possible moves considering the current state of the board. Prioritize moves that achieve line clears, then prioritize filling gaps. Lastly, consider immediate dropping to keep the game flowing.\n3. Choose the best move based on the analysis. Do not chose a move before doing all the steps to make sure you have the best possible move.\n\nStructure your response as a JSON, so as {"board_state", BOARD_STATE, "tetromino": TETROMINO, "explanation": EXPLANATION, "action": ACTION} where BOARD_STATE is the current state of the board described in 1-3 sentences, TETROMINO is the type of the falling tetromino (I, J, L, O, S, T, Z), EXPLANATION is your reasoning behind the move and ACTION is the string representing the chosen move. Do not add any more keys to the JSON. Your response should start with { and end with }.'

    img = PIL.Image.open(image_path)
    response = model.generate_content(
        contents=[img, prompt],
        generation_config=genai.types.GenerationConfig(
            # max_output_tokens=500,
            temperature=0.2,
        ),
        stream=False,
    )

    text = response.text
    print(text, "\n")
    stripped_text = text[text.index("{") : (text.index("}") + 1)]
    json = eval(stripped_text)
    return json["action"]


if os.path.exists("screens"):
    shutil.rmtree("screens")
os.mkdir("screens")

if os.path.exists("actions"):
    shutil.rmtree("actions")
os.mkdir("actions")

state_counter = 1

while True:
    time.sleep(1)
    image_path = f"screens/screenshot_{state_counter-1}.png"
    action = get_gemini_response(image_path=image_path)
    with open(f"actions/action_{state_counter}", "w") as fp:
        fp.write(action)
    state_counter += 1
