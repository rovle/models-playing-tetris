"""Cognitive error analysis for Tetris LLM benchmark.

Classifies reasoning failures by comparing model chain-of-thought
responses against ground truth board states saved during gameplay.

Error taxonomy:
  1. Piece misidentification — model names the wrong tetromino
  2. Invalid move — game engine rejected the action
  3. Plan-action mismatch — final action differs from all CoT proposals
  4. Line clear hallucination — model claims lines will clear but they don't
  5. Strategic quality — board quality delta (height/holes) per turn
"""

import argparse
import json
import os


PIECE_TYPES = {"I", "J", "L", "O", "S", "T", "Z"}

LINE_CLEAR_PHRASES = [
    "clear a line", "clear lines", "clearing a line", "clearing lines",
    "line clear", "clear the line", "clears a line", "clears the line",
    "complete a line", "complete the line", "completes a line",
    "completing a line", "complete a row", "complete the row",
    "completes a row", "completing a row", "clear a row", "clear the row",
    "clears a row", "clearing a row",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_ground_truths(game_path):
    gt_dir = f"{game_path}/ground_truth"
    if not os.path.isdir(gt_dir):
        return {}
    result = {}
    for fname in os.listdir(gt_dir):
        if not fname.endswith(".json"):
            continue
        counter = int(fname.split("_")[1].split(".")[0])
        with open(f"{gt_dir}/{fname}") as fp:
            result[counter] = json.load(fp)
    return result


def load_responses(game_path):
    resp_dir = f"{game_path}/responses"
    if not os.path.isdir(resp_dir):
        return {}
    result = {}
    for fname in sorted(os.listdir(resp_dir)):
        if not fname.startswith("response_") or not fname.endswith(".json"):
            continue
        counter = int(fname.split("_")[1].split(".")[0])
        with open(f"{resp_dir}/{fname}") as fp:
            result[counter] = json.load(fp)
    return result


def load_info(game_path):
    info_path = f"{game_path}/info.json"
    if not os.path.isfile(info_path):
        return {}
    with open(info_path) as fp:
        return json.load(fp)


# ---------------------------------------------------------------------------
# Error detectors
# ---------------------------------------------------------------------------

def normalize_piece_name(raw):
    """Extract a single piece letter from model output like 'L-piece', 'The L', etc."""
    if not raw:
        return None
    upper = raw.upper().strip()
    for p in PIECE_TYPES:
        if p in upper:
            return p
    return upper[:1] if upper else None


def detect_piece_misidentification(ground_truth, response):
    actual = ground_truth.get("current_piece")
    claimed_raw = response.get("tetromino", "")
    claimed = normalize_piece_name(claimed_raw)
    if actual is None or claimed is None:
        return {"checkable": False}
    error = actual != claimed
    return {"checkable": True, "error": error, "actual": actual, "claimed": claimed}


def detect_invalid_moves(ground_truths, turn_start, action_count):
    """Check action_success for each step in a model turn."""
    invalids = []
    for i in range(action_count):
        step = turn_start + 1 + i
        gt = ground_truths.get(step)
        if gt and gt.get("action_success") is False:
            invalids.append({
                "step": step,
                "action": gt.get("action_applied"),
            })
    return invalids


def detect_plan_action_mismatch(response):
    """Check if final action matches one of the proposed action sequences."""
    final = response.get("action", "")
    proposals = [
        response.get("action_proposal_1", ""),
        response.get("action_proposal_2", ""),
        response.get("action_proposal_3", ""),
    ]
    proposals = [p for p in proposals if p]
    if not proposals:
        return {"checkable": False}

    def normalize_actions(s):
        return ",".join(a.strip().lower() for a in s.split(",") if a.strip())

    final_norm = normalize_actions(final)
    proposal_norms = [normalize_actions(p) for p in proposals]
    error = final_norm not in proposal_norms
    return {
        "checkable": True,
        "error": error,
        "final_action": final,
        "proposals": proposals,
    }


def detect_line_clear_hallucination(ground_truths, response, turn_start, action_count):
    pre = ground_truths.get(turn_start)
    last_step = turn_start + action_count
    post = ground_truths.get(last_step)
    if not pre or not post:
        return {"checkable": False}

    lines_before = pre.get("lines_cleared", 0)
    lines_after = post.get("lines_cleared", 0)
    actual_cleared = lines_after - lines_before

    analysis_fields = [
        response.get("analysis_of_actions_1", ""),
        response.get("analysis_of_actions_2", ""),
        response.get("analysis_of_actions_3", ""),
        response.get("final_analysis", ""),
        response.get("move_analysis", ""),
    ]
    analysis_text = " ".join(f for f in analysis_fields if f).lower()

    claims_clear = any(phrase in analysis_text for phrase in LINE_CLEAR_PHRASES)

    return {
        "checkable": True,
        "claimed_line_clear": claims_clear,
        "actual_lines_cleared": actual_cleared,
        "hallucination": claims_clear and actual_cleared == 0,
    }


# ---------------------------------------------------------------------------
# Board quality metrics
# ---------------------------------------------------------------------------

def compute_board_quality(ground_truth):
    heights = ground_truth.get("column_heights", [0] * 10)
    holes = ground_truth.get("hole_depths", [0] * 10)
    height_sum = sum(heights)
    max_height = max(heights) if heights else 0
    mean_h = height_sum / len(heights) if heights else 0
    height_variance = sum((h - mean_h) ** 2 for h in heights) / len(heights) if heights else 0
    hole_count = sum(1 for d in holes if d > 0)
    hole_depth_sum = sum(holes)
    return {
        "height_sum": height_sum,
        "max_height": max_height,
        "height_variance": round(height_variance, 2),
        "hole_count": hole_count,
        "hole_depth_sum": hole_depth_sum,
    }


def compute_strategic_score(ground_truths, turn_start, action_count):
    pre = ground_truths.get(turn_start)
    post = ground_truths.get(turn_start + action_count)
    if not pre or not post:
        return None
    pre_q = compute_board_quality(pre)
    post_q = compute_board_quality(post)
    lines_gained = post.get("lines_cleared", 0) - pre.get("lines_cleared", 0)
    height_delta = post_q["height_sum"] - pre_q["height_sum"]
    holes_delta = post_q["hole_count"] - pre_q["hole_count"]
    move_score = (lines_gained * 100) - height_delta - (holes_delta * 10)
    return {
        "lines_gained": lines_gained,
        "height_delta": height_delta,
        "holes_delta": holes_delta,
        "move_score": move_score,
    }


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def count_actions(response):
    action_str = response.get("action", "")
    return len([a.strip() for a in action_str.split(",") if a.strip()])


def analyze_game(game_path):
    ground_truths = load_ground_truths(game_path)
    responses = load_responses(game_path)
    info = load_info(game_path)

    if not ground_truths:
        return None

    results = {
        "game_path": game_path,
        "model": info.get("model", "unknown"),
        "prompt_name": info.get("prompt_name", "unknown"),
        "total_turns": len(responses),
        "total_steps": max(ground_truths.keys(), default=0),
        "pieces_placed": info.get("pieces_count", 0),
        "lines_cleared": info.get("lines_cleared", 0),
        "score": info.get("score", 0),
        "errors": {
            "piece_misidentification": {"count": 0, "details": []},
            "invalid_move": {"count": 0, "details": []},
            "plan_action_mismatch": {"count": 0, "details": []},
            "line_clear_hallucination": {"count": 0, "details": []},
        },
        "board_quality_trajectory": [],
        "strategic_scores": [],
    }

    for resp_idx in sorted(responses.keys()):
        response = responses[resp_idx]
        gt = ground_truths.get(resp_idx)
        if not gt:
            continue

        action_count = count_actions(response)

        # 1. Piece misidentification
        piece_result = detect_piece_misidentification(gt, response)
        if piece_result.get("error"):
            results["errors"]["piece_misidentification"]["count"] += 1
            results["errors"]["piece_misidentification"]["details"].append(
                {"step": resp_idx, **piece_result}
            )

        # 2. Invalid moves
        invalids = detect_invalid_moves(ground_truths, resp_idx, action_count)
        results["errors"]["invalid_move"]["count"] += len(invalids)
        results["errors"]["invalid_move"]["details"].extend(invalids)

        # 3. Plan-action mismatch
        mismatch = detect_plan_action_mismatch(response)
        if mismatch.get("error"):
            results["errors"]["plan_action_mismatch"]["count"] += 1
            results["errors"]["plan_action_mismatch"]["details"].append(
                {"step": resp_idx, **mismatch}
            )

        # 4. Line clear hallucination
        lcr = detect_line_clear_hallucination(
            ground_truths, response, resp_idx, action_count
        )
        if lcr.get("hallucination"):
            results["errors"]["line_clear_hallucination"]["count"] += 1
            results["errors"]["line_clear_hallucination"]["details"].append(
                {"step": resp_idx, **lcr}
            )

        # Board quality at this turn
        bq = compute_board_quality(gt)
        results["board_quality_trajectory"].append({"step": resp_idx, **bq})

        # Strategic score
        ss = compute_strategic_score(ground_truths, resp_idx, action_count)
        if ss:
            results["strategic_scores"].append({"step": resp_idx, **ss})

    # Compute rates
    total = results["total_turns"]
    if total > 0:
        for err_type, err_data in results["errors"].items():
            err_data["rate"] = round(err_data["count"] / total, 4)

    # Average strategic score
    scores = results["strategic_scores"]
    if scores:
        results["avg_move_score"] = round(
            sum(s["move_score"] for s in scores) / len(scores), 2
        )

    return results


def merge_into_info(game_path, analysis):
    """Write cognitive analysis summary into info.json."""
    info_path = f"{game_path}/info.json"
    if not os.path.isfile(info_path):
        return
    with open(info_path) as fp:
        info = json.load(fp)
    info["cognitive_analysis"] = {
        "total_turns": analysis["total_turns"],
        "piece_misid_count": analysis["errors"]["piece_misidentification"]["count"],
        "piece_misid_rate": analysis["errors"]["piece_misidentification"].get("rate", 0),
        "invalid_move_count": analysis["errors"]["invalid_move"]["count"],
        "invalid_move_rate": analysis["errors"]["invalid_move"].get("rate", 0),
        "plan_action_mismatch_count": analysis["errors"]["plan_action_mismatch"]["count"],
        "plan_action_mismatch_rate": analysis["errors"]["plan_action_mismatch"].get("rate", 0),
        "line_clear_hallucination_count": analysis["errors"]["line_clear_hallucination"]["count"],
        "line_clear_hallucination_rate": analysis["errors"]["line_clear_hallucination"].get("rate", 0),
        "avg_move_score": analysis.get("avg_move_score"),
    }
    with open(info_path, "w") as fp:
        json.dump(info, fp, indent=2)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_summary(analysis):
    print(f"\n{'='*60}")
    print(f"Cognitive Error Analysis: {analysis['game_path']}")
    print(f"Model: {analysis['model']}  |  Prompt: {analysis['prompt_name']}")
    print(f"Turns: {analysis['total_turns']}  |  Pieces: {analysis['pieces_placed']}  "
          f"|  Lines: {analysis['lines_cleared']}  |  Score: {analysis['score']}")
    print(f"{'='*60}")

    for err_type, err_data in analysis["errors"].items():
        label = err_type.replace("_", " ").title()
        rate = err_data.get("rate", 0)
        print(f"  {label:30s}  {err_data['count']:4d}  ({rate:.1%})")

    avg_score = analysis.get("avg_move_score")
    if avg_score is not None:
        print(f"  {'Avg Move Score':30s}  {avg_score:7.1f}")
    print()


def print_details(analysis):
    for err_type, err_data in analysis["errors"].items():
        if not err_data["details"]:
            continue
        label = err_type.replace("_", " ").title()
        print(f"\n--- {label} Details ---")
        for d in err_data["details"]:
            step = d.get("step", "?")
            detail_str = ", ".join(f"{k}={v}" for k, v in d.items()
                                  if k not in ("step", "checkable"))
            print(f"  Step {step}: {detail_str}")


def find_instrumented_games():
    """Find all games that have ground_truth data."""
    base = "games_archive"
    if not os.path.isdir(base):
        return []
    games = []
    for folder in sorted(os.listdir(base)):
        game_path = f"{base}/{folder}"
        if os.path.isdir(f"{game_path}/ground_truth"):
            gt_files = os.listdir(f"{game_path}/ground_truth")
            if any(f.endswith(".json") for f in gt_files):
                games.append(game_path)
    return games


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cognitive error analysis for Tetris LLM games"
    )
    parser.add_argument("--game", type=int, help="Analyze a specific game number")
    parser.add_argument("--all", action="store_true", help="Analyze all instrumented games")
    parser.add_argument("--detail", action="store_true", help="Print per-step error details")
    parser.add_argument("--save", action="store_true", help="Merge results into info.json")
    args = parser.parse_args()

    if args.game:
        game_path = f"games_archive/game_{args.game}"
        analysis = analyze_game(game_path)
        if analysis is None:
            print(f"No ground truth data found for game {args.game}.")
        else:
            print_summary(analysis)
            if args.detail:
                print_details(analysis)
            if args.save:
                merge_into_info(game_path, analysis)
                print(f"Saved cognitive analysis to {game_path}/info.json")

    elif args.all:
        games = find_instrumented_games()
        if not games:
            print("No instrumented games found.")
        else:
            all_analyses = []
            for game_path in games:
                analysis = analyze_game(game_path)
                if analysis:
                    all_analyses.append(analysis)
                    print_summary(analysis)
                    if args.detail:
                        print_details(analysis)
                    if args.save:
                        merge_into_info(game_path, analysis)

            if all_analyses:
                print(f"\n{'='*60}")
                print(f"Aggregate across {len(all_analyses)} games")
                print(f"{'='*60}")
                for err_type in ["piece_misidentification", "invalid_move",
                                 "plan_action_mismatch", "line_clear_hallucination"]:
                    total_count = sum(a["errors"][err_type]["count"] for a in all_analyses)
                    total_turns = sum(a["total_turns"] for a in all_analyses)
                    rate = total_count / total_turns if total_turns else 0
                    label = err_type.replace("_", " ").title()
                    print(f"  {label:30s}  {total_count:4d} / {total_turns} turns  ({rate:.1%})")
                move_scores = [a["avg_move_score"] for a in all_analyses
                               if a.get("avg_move_score") is not None]
                if move_scores:
                    avg = sum(move_scores) / len(move_scores)
                    print(f"  {'Avg Move Score':30s}  {avg:7.1f}")

    else:
        parser.print_help()
