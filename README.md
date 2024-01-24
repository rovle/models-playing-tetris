<p align="center">
    <img src="https://github.com/rovle/tetris-ai/raw/main/.gfx/logo_original.png" alt="logo"/>
</p>

# Models playing Tetris

*Benchmarking various multimodal LLMs' ability to play Tetris.*


{video here 2x2 maybe?}

Can the current multimodal LLMs successfully play Tetris? We test GPT-4V, Gemini Pro Vision, and LLava 13b, with few-shot and chain of thought prompting, on this task. See a short summary of the results in the table below; for more details see the [Twitter thread] or the [Lesswrong post].

[table of results]

## The bounty for a better prompt setup

During our testing we observed that prompts significantly affect how well the model plays the game; having had only limited time and energy to prompt-craft, and not wanting our limited efforts to be the last word on models playing Tetris, we're announcing a **bounty** for the best prompt which beats our best prompt. Specifically, our best prompting setup for Gemini Pro Vision achieves XX placed pieces on average, and the best prompting setup for GPT-4V achieves YY placed pieces on average, and thus we pledge to award min(2*{number of pieces the method achieves}, 200) USD to
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
  --model MODEL         name of the model. Possible values: gemini-pro-vision, gpt-4-vision-preview, llava-13b, random, manual
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
python main.py --model gemini-pro-vision --temperature 0.4 --prompt_name complex_cot_prompt_n5_multiple_actions_v1 --example_ids 32 33
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
Where "action_type" denotes whether the prompt does allow for more than one action to be supplied per model's output (`multiple`) or not (`single`). After adding that, you can run
```console
python main.py --prompt_name your_prompt_name
```
to run games with your prompt. Do note that our parsing functions expects the action(s) to be returned in a JSON-like object within the model's outputs, so in particular it expects a parseable JSON enclosed within "{" and "}", with a key "action" or "actions", inside the model's output. You should therefore either **specify this in the prompt** (see the existing prompts for examples), or else rewrite the parsing function (``parse response` in `model_controller/models.py`) to match your prompting setup.

## Adding examples for few-shot prompting

(Supported for `gpt-4-vision-preview` and `gemini-pro-vision`.)

If you want to add an `(image, response)` pair as an example for few-shot prompting you should put the image into `assets/images` and add a dictionary entry to `examples.json`. Our current examples are optimized for being parsed as JSONs and added to the text in that way. See `examples.json` and `generate_response` method for the appropriate model in `model_controller/models.py`.

## The Tetris game

The implementation of Tetris used was originally made by [zeroize318](https://github.com/zeroize318) and it can be found here [here](https://github.com/zeroize318/tetris_ai).

