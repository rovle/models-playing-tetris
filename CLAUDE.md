# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Benchmarking multimodal LLMs' ability to play Tetris. The system screenshots a pygame Tetris board, sends it to an LLM via [litellm](https://docs.litellm.ai/), parses the model's move response, executes it in-game, and logs results. Any vision-capable model supported by litellm can be used (e.g., `anthropic/claude-opus-4-6`, `openai/gpt-4o`, `gemini/gemini-3-flash-preview`), plus `random` and `manual` players.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in API keys
```

Requires `ffmpeg` on PATH for post-game video creation.

## Commands

```bash
# Run a game (model names use litellm provider/model format)
uv run python main.py --model gemini/gemini-3-flash-preview --prompt_name complex_cot_prompt_n5_multiple_actions_v1 --example_ids 32 33

uv run python main.py --model anthropic/claude-opus-4-6 --prompt_name complex_cot_prompt_n5_multiple_actions_v1

# Via OpenRouter
uv run python main.py --model openrouter/google/gemini-3-flash-preview --prompt_name complex_cot_prompt_n5_multiple_actions_v1

# Analyze past games
uv run python lib/games_analysis.py --model gemini/gemini-3-flash-preview

# Generate video from a past game's screenshots (N = game number, default framerate=8)
uv run python -c "from lib.video_creation import create_video; create_video(N, framerate=4)"
```

No test suite exists.

## Architecture

### Dual-thread design (`main.py`)

Two threads run concurrently and coordinate via a shared JSON file (`logs/communications_log.json`):

1. **Game thread** — `tetris/game.py:Game.run()` renders pygame, captures screenshots to `games_archive/game_N/screens/`, reads action files from `games_archive/game_N/actions/`, executes moves, and writes game state to the communications log.
2. **Model thread** — `model_controller/run_model.py:test_model()` polls for new screenshots, sends them to the LLM, parses the response into actions, writes action files, and waits for the game thread to acknowledge via `state_counter` in the communications log.

### IPC: `CommunicationsLog` (`lib/game_agent_comms.py`)

A JSON-file-backed dict that both threads read/write for synchronization (`state_counter`, `game_over`, `finished_restart`, `shutdown_game`, etc.). Not thread-safe beyond retry-on-decode-error.

### Model abstraction (`model_controller/models.py`)

`LiteLLMModel` wraps `litellm.completion()` with `generate_response(prompt_name, example_ids, image_path)`. Accepts any litellm model string (e.g., `anthropic/claude-opus-4-6`). `RandomPlayer` and `ManualPlayer` bypass litellm. `get_model(model_name, temperature)` factory routes to the appropriate class. `parse_response()` extracts JSON `{"action": "..."}` from model output using `eval()`.

### Prompts & examples

- `assets/prompts.json` — prompt definitions with `action_type` (`single`/`multiple`) and `instructions` text
- `assets/examples.json` — few-shot examples linking image paths to expected responses
- New prompts: add to `prompts.json`, model output must contain a JSON object with `"action"` or `"actions"` key

### Game archive (`games_archive/`)

Each game gets `game_N/` with subdirs: `screens/` (PNG screenshots), `actions/` (one file per action), `responses/` (raw model output), and `info.json` (final stats). Post-game, `ffmpeg` generates an mp4 from screenshots.

### Tetris engine (`tetris/`)

Forked from [zeroize318/tetris_ai](https://github.com/zeroize318/tetris_ai). `Gamestate` manages the board grid, piece spawning, collision detection, scoring, and T-spin logic. `Game` wraps it with pygame GUI and the file-based action/screenshot loop. Valid actions: `left`, `right`, `down`, `drop`, `turn left`, `turn right`, `hold`.

## Key Conventions

- Model responses must contain a parseable JSON `{"action": "..."}` somewhere in the output text; `parse_response` finds the first `{...}` and `eval()`s it
- If a single action isn't `down` or `drop`, a `down` is auto-appended
- The `augmentation` field in prompts applies image transforms before sending to the model (works for all providers)
- `--endless` flag loops games indefinitely; without it, the process exits after one game
