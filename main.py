import threading
from lib.cli import parse_args
from model_controller.run_model import test_model
from tetris import game

def run_testing():
    test_model(args)

def run_game():
    game.start()

if __name__ == "__main__":
    args = parse_args()
    model_thread = threading.Thread(target=run_testing)
    game_thread = threading.Thread(target=run_game)

    model_thread.start()
    game_thread.start()

    model_thread.join()
    game_thread.join()
