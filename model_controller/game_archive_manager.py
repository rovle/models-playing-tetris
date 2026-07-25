import os
import json
from lib.game_agent_comms import CommunicationsLog


def create_new_game_folder(num):
    game_folder = f"games_archive/game_{num}"
    os.mkdir(game_folder)
    for name in ['screens', 'actions', 'responses', 'ground_truth']:
        os.mkdir(f"{game_folder}/{name}")

def save_action(game_number, state_counter, action):
    with open(f"games_archive/game_{game_number}/actions/action_{state_counter}", "w") as fp:
        fp.write(action)

def save_structured_response(
    game_number, screenshot_index, parsed_dict, raw_json, reasoning=None, metrics=None
):
    resp = dict(parsed_dict)
    resp["_raw_json"] = raw_json
    if reasoning:
        resp["reasoning"] = str(reasoning)
    if metrics:
        resp["_metrics"] = metrics
    path = f"games_archive/game_{game_number}/responses/response_{screenshot_index}.json"
    with open(path, "w") as fp:
        json.dump(resp, fp)


def _aggregate_metrics(game_number):
    """Add up cost and timing for a game from its saved responses."""
    folder = f"games_archive/game_{game_number}/responses"
    costs, durations, output_tokens = [], [], []
    resolved_model = None
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        try:
            with open(f"{folder}/{name}", "r") as fp:
                metrics = json.load(fp).get("_metrics") or {}
        except (json.JSONDecodeError, OSError):
            continue
        if metrics.get("total_cost_usd") is not None:
            costs.append(metrics["total_cost_usd"])
        if metrics.get("duration_ms") is not None:
            durations.append(metrics["duration_ms"])
        tokens = (metrics.get("usage") or {}).get("output_tokens")
        if tokens is not None:
            output_tokens.append(tokens)
        resolved_model = metrics.get("resolved_model") or resolved_model

    if not (costs or durations or output_tokens or resolved_model):
        return {}
    return {
        "resolved_model": resolved_model,
        "total_cost_usd": round(sum(costs), 4) if costs else None,
        "avg_move_duration_s": round(sum(durations) / len(durations) / 1000, 2)
        if durations
        else None,
        "total_output_tokens": sum(output_tokens) if output_tokens else None,
    }


def save_info(game_number, args):
    communications_log = CommunicationsLog()
    information_dict = {
        "tetris_seed": communications_log["tetris_seed"],
        "model": args.model,
        "temperature": args.temperature,
        "effort": getattr(args, "effort", None),
        "prompt_name": args.prompt_name,
        "example_ids": args.example_ids,
        "pieces_count": int(communications_log["pieces_count"]),
        "lines_cleared": int(communications_log["lines_cleared"]),
        "score": int(communications_log["score"]),
        "n_lines": communications_log["n_lines"],
        "t_spins": communications_log["t_spins"],
        "combo": int(communications_log["combo"]),
        **_aggregate_metrics(game_number),
    }
    with open(f"games_archive/game_{game_number}/info.json", "w") as fp:
        json.dump(information_dict, fp)
