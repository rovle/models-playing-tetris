import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", help="model name for AI generation", default="gemini-pro-vision"
    )
    parser.add_argument(
        "--temperature", type=float, help="temperature for AI generation", default=0.4
    )
    parser.add_argument(
        "--prompt_name", help="name of the prompt for AI generation"
    )
    parser.add_argument(
        "--example_ids",
        type=int,
        nargs="*",
        help="list of IDs of examples to use",
        default=[],
    )
    return parser.parse_args()
