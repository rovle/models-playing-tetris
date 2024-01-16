import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", help="model name for AI generation (gemini-pro-vision, gpt-4-vision-preview, llava-13b, random, manual)", default="gemini-pro-vision"
    )
    parser.add_argument(
        "--temperature", type=float, help="temperature for AI generation. Default is 0.4", default=0.4
    )
    parser.add_argument(
        "--prompt_name", help="name of the prompt for AI generation. See the possible values in assets/prompts.json"
    )
    parser.add_argument(
        "--example_ids",
        type=int,
        nargs="*",
        help="list of IDs of examples to use for few-shot prompting. See the possible values in assets/examples.json",
        default=[],
    )
    parser.add_argument(
        "--tetris_seed",
        type=int,
        help="seed for the Tetris game. If it is supplied all the games will be played with the same seed, i.e. the same sequence of pieces",
    )
    return parser.parse_args()
