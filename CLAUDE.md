# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Benchmarking multimodal LLMs' ability to play Tetris. The system screenshots a pygame Tetris board, sends it to an LLM via [litellm](https://docs.litellm.ai/), parses the model's move response, executes it in-game, and logs results. Any vision-capable model supported by litellm can be used (e.g., `anthropic/claude-fable-5-1`, `openai/gpt-6-astra`, `gemini/gemini-3.8-flash`), plus `random` and `manual` players.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in API keys
```

Requires `ffmpeg` on PATH for post-game video creation.

## Commands

```bash
# Run a game (model names use litellm provider/model format)
uv run python main.py --model gemini/gemini-3.8-flash --prompt_name minimal_v1

uv run python main.py --model anthropic/claude-fable-5-1 --prompt_name minimal_v1

# Few-shot: reasoning_few_shot_v1 expects examples with an analysis field (ids 34 to 36)
uv run python main.py --model anthropic/claude-fable-5-1 --prompt_name reasoning_few_shot_v1 --example_ids 34 35 36

# Via OpenRouter, with reasoning at the level set by --effort
uv run python main.py --model openrouter/openai/gpt-6-astra --prompt_name minimal_v1 --reasoning --effort low

# Via the local Claude Code CLI, billed to whatever account it is logged in with
uv run python main.py --model claude-code/opus --prompt_name minimal_v1 --effort high

# Analyze past games
uv run python lib/games_analysis.py --model gemini/gemini-3.8-flash

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

`LiteLLMModel` wraps `litellm.completion()` with `generate_response(prompt_name, example_ids, image_path)`. Accepts any litellm model string (e.g., `anthropic/claude-fable-5-1`). `RandomPlayer` and `ManualPlayer` bypass litellm. `ClaudeCodeModel` (`claude_code_model.py`) shells out to the local `claude` CLI for `claude-code/` model names; see `docs/claude_code_backend.md`. `get_model(model_name, temperature)` factory routes to the appropriate class. `parse_response()` extracts JSON `{"action": "..."}` from model output using `json.loads()`.

Every backend builds its prompt through `model_controller/prompt_builder.py`, which emits provider-agnostic blocks and adapts them per backend, so runs stay comparable. Backends that do not use litellm raise `ModelCallError` (`model_controller/errors.py`) so the retry loop in `run_model.py` catches them the same way.

### Prompts & examples

- `assets/prompts/<name>.md` — one markdown file per prompt with YAML frontmatter (`action_type`, optional `augmentation`); body is the instructions text. Loaded by `lib/prompts.py:load_prompts()`. Filename (without extension) is the value passed to `--prompt_name`.
- `assets/examples.json` — few-shot examples linking image paths to expected responses
- New prompts: drop a new `.md` file into `assets/prompts/`. Model output must contain a JSON object with `"action"` or `"actions"` key.

### Game archive (`games_archive/`)

Each game gets `game_N/` with subdirs: `screens/` (PNG screenshots), `actions/` (one file per action), `responses/` (raw model output), and `info.json` (final stats). Post-game, `ffmpeg` generates an mp4 from screenshots.

### Tetris engine (`tetris/`)

Forked from [zeroize318/tetris_ai](https://github.com/zeroize318/tetris_ai). `Gamestate` manages the board grid, piece spawning, collision detection, scoring, and T-spin logic. `Game` wraps it with pygame GUI and the file-based action/screenshot loop. Valid actions: `left`, `right`, `down`, `drop`, `turn left`, `turn right`, `hold`.

## Key Conventions

- Model responses must contain a parseable JSON `{"action": "..."}` somewhere in the output text; `parse_response` finds the first `{...}` and `eval()`s it
- If a single action isn't `down` or `drop`, a `down` is auto-appended
- The `augmentation` field in prompts applies image transforms before sending to the model (works for all providers)
- `--endless` flag loops games indefinitely; without it, the process exits after one game
- `--max_tokens` (default 16000) caps output per move. Gemini 3+ counts thinking tokens against that cap, so a model that thinks past it returns empty content and the turn fails JSON validation. Raise it for heavy thinkers
- `--reasoning` requests thinking at the level set by `--effort` (default `high`). Without it the request carries no reasoning settings and the provider default applies, so `--effort` is ignored. OpenRouter gets `extra_body.reasoning.effort`, direct providers get litellm's `reasoning_effort`, and `claude-code/` always passes `--effort` to the CLI. `xhigh` and `max` are accepted by OpenRouter and Claude Code only
- Gemini 3+ called through `gemini/` or `vertex_ai/` gets `includeThoughts: true` so thought summaries land in `responses/`
- `--temperature` defaults to `None`, meaning the request carries no temperature and the provider default applies. Recent OpenAI and Gemini reasoning models reject or ignore an explicit temperature, so leave it unset for benchmarks
- `info.json` records `temperature` (`null` means provider default), `effort`, and `reasoning` (whether `--reasoning` was passed, so whether `effort` was in effect)
- `--prompt_name` defaults to `minimal_v1`. `reasoning_few_shot_v1` needs examples with an `analysis` field (ids 34 to 36 in `assets/examples.json`); older ids use the legacy multi-field format
- litellm has no price entry for `gpt-6-astra`, so cost fields in `info.json` may be zero for that model
