import io
import base64
import json
import random
from datetime import datetime

import litellm

litellm.suppress_debug_info = True
from dotenv import load_dotenv

import lib.image_transformation as img_transform
from lib.json_utils import extract_json_object

load_dotenv()

with open("assets/prompts.json", "r") as prompt_file:
    prompts = json.load(prompt_file)
with open("assets/examples.json", "r") as example_file:
    examples = json.load(example_file)


class LiteLLMModel:
    def __init__(self, model_name, temperature=0.4):
        self.model_name = model_name
        self.temperature = temperature

    def generate_response(self, prompt_name, example_ids, image_path):
        prompt = prompts.get(prompt_name, {})
        instructions = prompt.get("instructions", "")
        augmentation = prompt.get("augmentation")

        # Build few-shot example messages
        example_messages = []
        for example in examples:
            if example["id"] in example_ids:
                example_dict = {
                    k: v for i, (k, v) in enumerate(example.items()) if i > 1
                }
                img_b64 = img_transform.encode_image(example["image_path"])
                example_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Current board:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}"
                                },
                            },
                        ],
                    }
                )
                example_messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(example_dict),
                    }
                )

        # Current board image(s) — augmented variants + original
        image_content = []
        if augmentation:
            for pil_img in img_transform.apply_augmentations(image_path, augmentation):
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                aug_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                image_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{aug_b64}"},
                    }
                )
        current_img_b64 = img_transform.encode_image(image_path)
        image_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{current_img_b64}"},
            }
        )

        current_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Current board:"},
                *image_content,
            ],
        }

        messages = [
            {"role": "system", "content": instructions},
            *example_messages,
            current_msg,
        ]

        response = litellm.completion(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=10000,
            num_retries=10,
        )

        return response.choices[0].message.content


class RandomPlayer:
    def __init__(self, model_name="random", temperature=0.4):
        self.model_name = model_name
        self.temperature = temperature

    def generate_response(self, prompt_name, example_ids, image_path):
        actions = ["left", "right", "down", "drop", "turn right", "turn left"]
        return f'{{"action": "{random.choice(actions)}" }}'


class ManualPlayer:
    def __init__(self, model_name="manual", temperature=0.4):
        self.model_name = model_name
        self.temperature = temperature

    def generate_response(self, prompt_name, example_ids, image_path):
        return f"{{\"action\": \"{input('Enter your next move: ')}\" }}"


def get_model(model_name, temperature=0.4):
    if model_name == "random":
        return RandomPlayer(model_name, temperature)
    if model_name == "manual":
        return ManualPlayer(model_name, temperature)
    return LiteLLMModel(model_name, temperature)


def parse_response(prompt_name, response_text):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}]", response_text, "\n")

    prompt = prompts.get(prompt_name, {})
    action_type = prompt.get("action_type", None)

    stripped_text = extract_json_object(response_text)
    data = eval(stripped_text)
    action = data.get("action", None)

    if "," in action:
        action_arr = action.split(",")
        stripped_action_arr = (
            [action_arr[0].strip()]
            if action_type == "single"
            else [a.strip() for a in action_arr]
        )
    else:
        stripped_action_arr = [action]

    if len(stripped_action_arr) == 1:
        action = stripped_action_arr[0]
        if action not in ["down", "drop"]:
            stripped_action_arr = [action, "down"]
    return stripped_action_arr, stripped_text, data
