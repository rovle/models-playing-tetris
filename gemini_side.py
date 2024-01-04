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

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--manual", help="manual mode", action="store_true")
args = parser.parse_args()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro-vision")
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def generate_ai_response(image_path):
    prompt = 'Imagine you are a Tetris player with superhuman abilities. You have the power to see 5 moves ahead and can instantly calculate the best possible move for any given board state. You also have perfect hand-eye coordination and can execute any move with precision.\n\nI am presenting you with an image of a Tetris board at its current state. The board is represented by a grid of 10 columns and 20 rows. The empty cells are grey while the Tetrominoes are represented by red color. The possible moves are:\n\nLeft: "left"\nRight: "right"\nDown: "down"\nDrop: "drop"\nRotate clockwise: "turn right"5\nRotate counterclockwise: "turn left"\n\nThe game starts with a random Tetromino falling from the top of the board. You can move the falling Tetromino left or right, and also rotate it clockwise or counterclockwise. You can also drop the Tetromino immediately to the bottom.\n\nWhen a complete row of blocks is formed, it disappears and the blocks above it fall down. Points are scored for each row that is cleared. The game ends when the blocks reach the top of the board.\n\nYour goal is to play Tetris and achieve the highest possible score by maximizing cleared lines and minimizing block gaps. Let\'s think step by step:\n1. Analyze the board, the position of the current blocks and where the current tetromino would best slot in.\n2. Rank the possible moves considering the current state of the board. Prioritize moves that achieve line clears, then prioritize filling gaps. Lastly, consider immediate dropping to keep the game flowing.\n3. Choose the best move based on the analysis. Do not chose a move before doing all the steps to make sure you have the best possible move.\n\nStructure your response as a JSON, so as {"board_state", BOARD_STATE, "tetromino": TETROMINO, "explanation": EXPLANATION, "action": ACTION} where BOARD_STATE is the current state of the board described in 1-3 sentences, TETROMINO is the type of the falling tetromino (I, J, L, O, S, T, Z), EXPLANATION is your reasoning behind the move and ACTION is the string representing the chosen move. Do not add any more keys to the JSON. Your response should start with { and end with }.\n\n'

    example_img_1 = PIL.Image.open("assets/images/example_1.png")
    example_1_response = '{"board_state": "The board is empty.", "tetromino": "Z", "explanation": "With an empty board, you have the most flexibility in placing the Z tetromino. You can drop it anywhere without affecting existing lines.", "action": "drop"}\n\n'

    example_img_2 = PIL.Image.open("assets/images/example_2.png")
    example_2_response = '{"board_state": "The board has a T tetromino on the bottom center.", "tetromino": "I", "explanation": "Since there are 4 empty spaces on the left side of the bottom row, moving the I tetromino left will allow you to reach the edge of the board and potentially clear the line in the next few moves.", "action": "left"}\n\n'

    example_img_3 = PIL.Image.open("assets/images/example_3.png")
    example_3_response = '{"board_state": "The board is filled with 3 tetrominoes on the bottom right side. The rightmost column, the 3rd column from the right, and the first 4 columns from the left are all empty.", "tetromino": "J", "explanation": "Dropping the J tetromino would be the best move to fill the empty space to the left of the T tetromino and potentially clear a line.", "action": "drop"}\n\n'

    example_img_4 = PIL.Image.open("assets/images/example_4.png")
    example_4_response = '{"board_state": "The board has a yellow square tetromino on the bottom center and blue I tetromino lying on its side to the right of it. The left side of the board is empty.", "tetromino": "O", "explanation": "To clear a line efficiently, it\'s best to move the yellow square tetromino left. Since the left side of the board is empty, this allows you to potentially drop it later and fill two bottom cells, setting you up for a line clear.", "action": "left"}\n\n'

    example_img_5 = PIL.Image.open("assets/images/example_5.png")
    example_5_response = '{"board_state": "The board has a tall stack of blocks in the center, reaching 10 rows high. The sides of the board are empty.", "tetromino": "L", "explanation": "The current game strategy hasn\'t been ideal. It\'s generally better to fill the corners of the board to prevent blocks from stacking up too high in one area. In this case, the best move would be to move the L tetromino to the right, all the way against the wall, and then carefully lower it to fill any gaps in the bottom row. This will start to create a more even foundation for future blocks.", "action": "right"}\n\n'

    img = PIL.Image.open(image_path)

    response = model.generate_content(
        contents=[
            prompt,
            example_img_1,
            example_1_response,
            example_img_2,
            example_2_response,
            example_img_3,
            example_3_response,
            example_img_4,
            example_4_response,
            example_img_5,
            example_5_response,
            img,
        ],
        generation_config=genai.types.GenerationConfig(
            # max_output_tokens=500,
            temperature=0.4,
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


def get_gemini_response(image_path=None):
    if args.manual:
        return get_user_input()

    retry_count = 0
    while retry_count < 50:
        try:
            response_text = generate_ai_response(image_path)
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

    input("Press Enter when you have started the game...")
    while True:
        time.sleep(1)
        image_path = f"screens/screenshot_{state_counter-1}.png"
        action = get_gemini_response(image_path=image_path)
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
            # move the file pieces_count.txt to game_number folder
            shutil.move(
                "pieces_count.txt",
                f"previous_games/game_{game_number}/pieces_count.txt",
            )
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
