import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        help="Model name in litellm format: anthropic/claude-opus-4-6, openai/gpt-4o, "
        "gemini/gemini-3-flash-preview, openrouter/google/gemini-3-flash-preview, etc. "
        "Prefix with claude-code/ to play through the Claude Code CLI on whatever "
        "account it is logged in with, e.g. claude-code/opus. "
        "Special values: random, manual",
        required=True,
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="temperature with which to sample the model. Default is 0.4. "
        "Ignored by claude-code/ models, since the CLI has no temperature flag",
        default=0.4,
    )
    parser.add_argument(
        "--prompt_name",
        help="name of the prompt to use. See available prompts in assets/prompts/ (filename without .md extension)",
    )
    parser.add_argument(
        "--example_ids",
        type=int,
        nargs="*",
        help="optional list of IDs of examples for few-shot prompting. See possible values in assets/examples.json",
        default=[],
    )
    parser.add_argument(
        "--tetris_seed",
        type=int,
        help="seed for the Tetris game. If it is supplied all the games will be played with the same seed, i.e. the same sequence of pieces",
    )
    parser.add_argument(
        "--endless",
        action="store_true",
        help="if supplied, the script runs new games until stopped manually",
    )
    parser.add_argument(
        "--provider",
        help="OpenRouter provider slug to route requests to a specific provider/endpoint. "
        "Examples: google-ai-studio, google-vertex. "
        "Only applies to openrouter/ models.",
    )
    parser.add_argument(
        "--reasoning",
        action="store_true",
        help="Enable reasoning/thinking for the model via OpenRouter. "
        "Only applies to openrouter/ models.",
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="How much the model should think before answering. "
        "Only applies to claude-code/ models.",
    )
    return parser.parse_args()
