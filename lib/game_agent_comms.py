import json

def create_new_communications_log():
    with open("logs/communications_log.json", "w") as fp:
        json.dump(
                {
                    "state_counter": "-",
                    "game_over": "-",
                    "finished_restart": "-",
                    "pieces_count" : "-"
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
    with open("logs/communications_log.json", "r") as fp:
        log = json.load(fp)
    return log[key]