import json
import os

class CommunicationsLog:
    def __init__(self, filename="logs/communications_log.json",
                 restart_log=False):
        self.filename = filename
        self.log = None
        self.restart_log = restart_log
        # Initialize the log file
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        if self.restart_log or (not os.path.exists(filename)):
            self.init_log_file()

    def init_log_file(self):
        with open(self.filename, "w") as fp:
            json.dump({
                "tetris_seed": None,
                "state_counter": None,
                "game_over": None,
                "finished_restart": None,
                "score": None,
                "lines_cleared": None,
                "pieces_count" : None,
                "n_lines": None,
                "t_spins": None,
                "combo": None,
                "endless" : False,
                "shutdown_game": None
            },
            fp)
        self.log = {}

    def __getitem__(self, key):
        self.read_log_file()
        return self.log[key]

    def __setitem__(self, key, value):
        self.update_log_file(key, value)

    def read_log_file(self):
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                with open(self.filename, "r") as fp:
                    self.log = json.load(fp)
                    return
            except json.decoder.JSONDecodeError:
                retry_count += 1

        if self.log is None:
            print(f"Failed to load {self.filename} after {max_retries} retries")

    def update_log_file(self, key, value):
        self.read_log_file()
        self.log[key] = value
        with open(self.filename, "w") as fp:
            json.dump(self.log, fp)