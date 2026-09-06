import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        help="Model name in litellm format: anthropic/claude-fable-5-1, openai/gpt-6-astra, "
        "gemini/gemini-3.8-flash, openrouter/openai/gpt-6-astra, etc. "
        "Prefix with claude-code/ to play through the Claude Code CLI on whatever "
        "account it is logged in with, e.g. claude-code/opus. "
        "Special values: random, manual",
        required=True,
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="temperature with which to sample the model. When omitted, the request "
        "carries no temperature and the provider default applies, which is what "
        "the model vendors recommend for reasoning models. "
        "Ignored by claude-code/ models, since the CLI has no temperature flag",
        default=None,
    )
    parser.add_argument(
        "--prompt_name",
        default="minimal_v1",
        help="name of the prompt to use. See available prompts in assets/prompts/ "
        "(filename without .md extension). Default is minimal_v1",
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
        help="Enable reasoning/thinking for the model at the level set by --effort. "
        "Ignored by claude-code/ models, which always reason.",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=16000,
        help="Output token cap per move. On Gemini 3+ and other reasoning models the "
        "thinking tokens count against this cap, so a low value returns an empty "
        "response. Default is 16000. Ignored by claude-code/ models.",
    )
    parser.add_argument(
        "--effort",
        choices=["minimal", "low", "medium", "high", "xhigh", "max"],
        default="high",
        help="How much the model should think before answering. Default is high. "
        "Applies to claude-code/ models always, and to other models when "
        "--reasoning is passed. xhigh and max are accepted by claude-code/ and "
        "openrouter/ only; direct providers may reject them.",
    )
    return parser.parse_args()
