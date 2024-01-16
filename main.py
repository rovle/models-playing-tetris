import threading
from lib.cli import parse_args
from ai_interaction import model_manager
from tetris import game

def run_model_manager():
    model_manager.manage_model(args)

def run_game():
    game.start()

if __name__ == "__main__":
    args = parse_args()
    ai_model_thread = threading.Thread(target=run_model_manager)
    game_thread = threading.Thread(target=run_game)

    ai_model_thread.start()
    game_thread.start()

    ai_model_thread.join()
    game_thread.join()
