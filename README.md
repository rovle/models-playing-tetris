<p align="center">
    <img src="https://github.com/rovle/tetris-ai/raw/main/.gfx/logo_original.png" alt="logo"/>
</p>

# Models playing Tetris

*Benchmarking various multimodal LLMs' ability to play Tetris.*

https://github.com/rovle/models-playing-tetris/assets/29806640/5bc1de42-49c8-4e4c-9676-0025536de99d

Can the current multimodal LLMs successfully play Tetris? We test GPT-4V, Gemini Pro Vision, and LLava 13b, with few-shot and chain of thought prompting, on this task. See a short summary of the results in the table below; for more details see the [X (Twitter) thread](https://twitter.com/magabrielagc/status/1753086983658713482) or the [Lesswrong post](https://www.lesswrong.com/posts/vk3JmXhNHi8zyJrfP/putting-multimodal-llms-to-the-tetris-test).

| Model | Basic prompt | Few-shot (k=2) | Chain of Thought | CoT + Few-shot (k=2) |
|-------|--------------|----------------|-------------------|----------------------|
| GPT-4V (single move per screenshot) | 13.2 | * | 13.1 | * |
| GPT-4V (multiple moves per screenshot) | 19.6 | 16.5 | 20.9 | 21.2 |
| Gemini Pro Vision (single move per screenshot) | 14.4 | 12.4 | 11.36*** | 16.04 |
| Gemini Pro Vision (multiple moves per screenshot) | 11.08*** | 19.52 | 11.76 | 19.96 |
| LLaVA-13b (multiple moves per screenshot) | 8.6*** | ** | 10.7*** | ** |

\*Skipped due to high API costs for single move games.

\**Skipped due to the API we used not supporting multiple images.

\***Random move play yields on average about 11.5 pieces placed.

## The bounty for a better prompt setup

During our testing we observed that prompts significantly affect how well the model plays the game; having had only limited time and energy to prompt-craft, and not wanting our limited efforts to be the last word on models playing Tetris, we're announcing a **bounty** for the best prompt which beats our best prompt. Specifically, our best prompting setup for Gemini Pro Vision achieves 19.96 placed pieces on average, and the best prompting setup for GPT-4V achieves 21.2 placed pieces on average, and thus we pledge to award min(2*{number of pieces the method achieves}, 200) USD to
1) The best solution received by the end of February 2024, tested on at least 10 games, which beats our prompting setup for either of those two models by at least 10 pieces placed.
2) If no solutions are sent by the end of February 2024, then the first solution sent to us after February 2024 which beats our best prompt by at least 10 pieces for one of those two models.

For more details on the bounty, see [Bounty details](bounty_details.md).

# Usage

## Development Setup Instructions

```console
# create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# install the dependencies
pip install -r requirements.txt

# set your API keys in .env
cp .env.example .env
```

## Testing a specific model

Run main.py and provide the arguments choosing the model and detailing the prompting setup.

Usage:

```console
usage: main.py [-h] [--model MODEL] [--temperature TEMPERATURE] [--prompt_name PROMPT_NAME] [--example_ids [EXAMPLE_IDS ...]] [--tetris_seed TETRIS_SEED] [--endless]

options:
  -h, --help            show this help message and exit
  --model MODEL         name of the model. Possible values: gpt-4o, gpt-4o-2024-11-20, gpt-4o-mini, o1, o1-mini, claude-3-5-sonnet-latest, claude-3-opus-latest, gemini-1.5-pro, gemini-1.5-flash, gemini-exp-1206, gemini-exp-1121, llava-13b, random, manual
  --temperature TEMPERATURE
                        temperature with which to sample the model. Default is 0.4
  --prompt_name PROMPT_NAME
                        name of the prompt to use. See possible values in assets/prompts.json
  --example_ids [EXAMPLE_IDS ...]
                        optional list of IDs of examples for few-shot prompting. See possible values in assets/examples.json
  --tetris_seed TETRIS_SEED
                        seed for the Tetris game. If it is supplied all the games will be played with the same seed, i.e. the same sequence of pieces
  --endless             if supplied, the script runs new games until stopped manually
```

Example command:

```console
python main.py --model gemini-1.5-flash --temperature 0.4 --prompt_name complex_cot_prompt_n5_multiple_actions_v1 --example_ids 32 33
```

## Evaluating model performance

Run lib/games_analysis.py and provide argument on which values to filter the games.

Usage:

```console
usage: games_analysis.py [-h] [--model MODEL] [--temperature TEMPERATURE] [--prompt_name PROMPT_NAME] [--example_ids [EXAMPLE_IDS ...]] [--tetris_seed TETRIS_SEED]

options:
  -h, --help            show this help message and exit
  --model MODEL
  --temperature TEMPERATURE
  --prompt_name PROMPT_NAME
  --example_ids [EXAMPLE_IDS ...]
                        -1 to specify games without examples
  --tetris_seed TETRIS_SEED
```

For example, `python lib/games_analysis.py --model gpt-4-vision-preview` returns the statistics — average amount pieces placed, average amount of lines cleared, etc. – for all the finished games with `gpt-4-vision-preview` model. It also shows more detailed breakdown of all the argument permutations that were passed alongside `model gpt-4-vision-preview`.

## Adding your own prompts

New prompts should be added as a dictionary entry in the `assets/prompts.json`. Specifically you should add a new key, value pair:
```json
"your_prompt_name": {
    "action_type": "single/multiple",
    "instructions": "your_prompt_here"
}
```
Where "action_type" denotes whether the prompt allows for more than one action to be supplied per model's output (`multiple`) or not (`single`). After adding that, you can run
```console
python main.py --prompt_name your_prompt_name
```
to run games with your prompt. Do note that our parsing functions expects the action(s) to be returned in a JSON-like object within the model's outputs, so in particular it expects a parseable JSON enclosed within "{" and "}", with a key "action" or "actions" and a string value containing either one action, or comma-separated actions, respectively, inside the model's output. You should therefore either **specify this in the prompt** (see the existing prompts for examples), or else rewrite the parsing function (`parse response` in `model_controller/models.py`) to match your prompting setup.

## Adding examples for few-shot prompting

(Supported for `gpt-4-vision-preview` and `gemini-pro-vision`.)

If you want to add an `(image, response)` pair as an example for few-shot prompting you should put the image into `assets/images` and add a dictionary entry to `examples.json`. Our current examples are optimized for being parsed as JSONs and added to the text in that way. See `examples.json` and `generate_response` method for the appropriate model in `model_controller/models.py`.

## The Tetris game

The implementation of Tetris used was originally made by [zeroize318](https://github.com/zeroize318) and it can be found here [here](https://github.com/zeroize318/tetris_ai).

