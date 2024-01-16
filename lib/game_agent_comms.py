import json

def create_new_communications_log():
    with open("logs/communications_log.json", "w") as fp:
        json.dump(
                {
                    "state_counter": "-",
                    "game_over": "-",
                    "finished_restart": "-",
                    "score": "-",
                    "lines_cleared": "-",
                    "pieces_count" : "-",
                    "n_lines": "-",
                    "t_spins": "-",
                    "combo": "-"
                },
                fp)
    return None

def update_communications_log(key, value):
    with open("logs/communications_log.json", "r") as fp:
        log = json.load(fp)
    log[key] = value
    with open("logs/communications_log.json", "w") as fp:
        json.dump(log, fp)
    return None
  
def read_communications_log(key):
    max_retries = 3
    retry_count = 0
    log = None

    while retry_count < max_retries:
        try:
            with open("logs/communications_log.json", "r") as fp:
                log = json.load(fp)
                return log[key]
        except json.decoder.JSONDecodeError:
            retry_count += 1

    if log is None:
        print("Failed to load communications_log.json after ${max_retries} retries")
        return None