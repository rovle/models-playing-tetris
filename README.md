# README

This project is dedicated to assessing and benchmarking the performance of Multi-modal Large Language Models (MLLMs) in the context of playing the classic Tetris game. The primary focus is on evaluating their capability to analyze the visual representation of the game board and provide optimal move suggestions.

The project offers compatibility with Gemini Pro Vision by Google, GPT-4V by OpenAI, and LLaVA. It employs techniques like few-shot and chain-of-thought prompting to improve the models' overall performance. Additionally, the project includes functionality for evaluating and grading the gameplay performance of the models.

## Development Setup Instructions

```python
# create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# install the dependencies
pip install -r requirements.txt

# set your API keys in .env
cp .env.example .env
```

## Running the game

Run main.py and provide the desired arguments.

Usage:

```shell
usage: main.py [-h] [--model MODEL] [--temperature TEMPERATURE] [--prompt_name PROMPT_NAME] [--example_ids [EXAMPLE_IDS ...]] [--tetris_seed TETRIS_SEED] [--endless]

options:
  -h, --help            show this help message and exit
  --model MODEL         name of the model. Possible values: gemini-pro-vision, gpt-4-vision-preview, llava-13b, random, manual
  --temperature TEMPERATURE
                        temperature for the model. Default is 0.4
  --prompt_name PROMPT_NAME
                        name of the prompt to use. See possible values in assets/prompts.json
  --example_ids [EXAMPLE_IDS ...]
                        optional list of IDs of examples for few-shot prompting. See possible values in assets/examples.json
  --tetris_seed TETRIS_SEED
                        seed for the Tetris game. If it is supplied all the games will be played with the same seed, i.e. the same sequence of pieces
  --endless             if supplied, the script runs new games until stopped manually
```

Example command:

```shell
python main.py --model gemini-pro-vision --temperature 0.4 --prompt_name complex_cot_prompt_n5_multiple_actions_v1 --example_ids 32 33
```

## Evaluating model performance

Run lib/games_analysis.py and provide the desired arguments.

Usage:

```shell
games_analysis.py [-h] [--model MODEL] [--temperature TEMPERATURE] [--prompt_name PROMPT_NAME] [--example_ids [EXAMPLE_IDS ...]] [--tetris_seed TETRIS_SEED]

options:
  -h, --help
  --model MODEL
  --temperature TEMPERATURE
  --prompt_name PROMPT_NAME
  --example_ids [EXAMPLE_IDS ...]
  --tetris_seed TETRIS_SEED
```
