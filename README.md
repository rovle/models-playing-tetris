# README

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

```bash
usage: main.py [-h] [--model MODEL] [--temperature TEMPERATURE] [--prompt_name PROMPT_NAME] [--example_ids [EXAMPLE_IDS ...]]

options:
  -h, --help            show this help message and exit
  --model MODEL         model name for AI generation (gemini-pro-vision, gpt-4-vision-preview, llava-13b, random, manual)
  --temperature TEMPERATURE
                        temperature for AI generation. Default is 0.4
  --prompt_name PROMPT_NAME
                        name of the prompt for AI generation. See the possible values in assets/prompts.json
  --example_ids [EXAMPLE_IDS ...]
                        list of IDs of examples to use for few-shot prompting. See the possible values in assets/examples.json
  --tetris_seed TETRIS_SEED
                        seed for the Tetris game. If it is supplied all the games will be played with the same seed, i.e. the same sequence of pieces
```

Example command:

```bash
python main.py --model gpt-4-vision-preview --temperature 0.7 --prompt_name complex_cot_prompt_n5_multiple_actions_v1 --example_ids 32 33
```
