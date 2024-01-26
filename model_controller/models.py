import os
from abc import ABC, abstractmethod
import json
import pdb
import requests
import random
from dotenv import load_dotenv

from PIL import Image
import google.generativeai as genai
import replicate

import lib.image_transformation as img_transform

load_dotenv()

with open("assets/prompts.json", "r") as prompt_file:
    prompts = json.load(prompt_file)
with open("assets/examples.json", "r") as example_file:
    examples = json.load(example_file)


class BaseModel(ABC):
    def __init__(self, model_name, temperature):
        self.model_name = model_name
        self.temperature = temperature

    @abstractmethod
    def generate_response(self, prompt_name, example_ids, image_path):
        pass


class GeminiProVision(BaseModel):
    def __init__(self, model_name, temperature):
        super().__init__(model_name, temperature)
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model_name)

    def generate_response(self, prompt_name, example_ids, image_path):
        prompt = prompts.get(prompt_name, {})
        instructions = prompt.get("instructions", None)
        augmentation = prompt.get("augmentation", None)

        example_responses = []
        example_imgs = []
        for example in examples:
            if example["id"] in example_ids:
                example_dict = {k: v for i, (k, v) in enumerate(example.items()) if i > 1}
                example_responses.append(example_dict)
                example_imgs.append(Image.open(example["image_path"]))

        example_responses = [json.dumps(example) for example in example_responses]

        example_images_and_responses = []
        for pair in zip(example_imgs, example_responses):
            example_images_and_responses.extend(pair)

        current_board_img = Image.open(image_path)
        if augmentation:
            current_board_imgs = img_transform.apply_augmentations(
                image_path, augmentation
            ) + [current_board_img]
        else:
            current_board_imgs = [current_board_img]

        response = self.model.generate_content(
            contents=[
                instructions,
                *example_images_and_responses,
                *current_board_imgs,
            ],
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
            ),
            stream=False,
        )

        return response.text

class Gpt4VisionPreview(BaseModel):
    def __init__(self, model_name, temperature):
        super().__init__(model_name, temperature)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = "gpt-4-vision-preview"

    def generate_response(self, prompt_name, example_ids, image_path):
        prompt = prompts.get(prompt_name, {})
        instructions = prompt.get("instructions", None)
        agumentation = prompt.get("agumentation", None)

        example_responses = []
        example_imgs = []
        for example in examples:
            if example["id"] in example_ids:
                example_dict = {k: v for i, (k, v) in enumerate(example.items()) if i > 1}
                example_responses.append(example_dict)
                example_imgs.append(img_transform.encode_image(example["image_path"]))

        example_responses = [json.dumps(example) for example in example_responses]

        example_images_and_responses = []
        for img, response in zip(example_imgs, example_responses):
            example_images_and_responses.append(
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}
            )
            example_images_and_responses.append({"type": "text", "text": response})

        current_board_img = img_transform.encode_image(image_path)

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "system",
                    "content": "You are `gpt-4-vision-preview`, the latest OpenAI model that can describe images provided by the user in extreme detail. The user has attached an image to this message for you to analyse, there is MOST DEFINITELY an image attached, you will never reply saying that you cannot see the image because the image is absolutely and always attached to this message.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instructions},
                        *example_images_and_responses,
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{current_board_img}"
                            },
                        },
                    ],
                },
            ],
            "max_tokens": 3000,
            "temperature": self.temperature,
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )

        response = response.json()
        print(response)
        response_text = response["choices"][0]["message"]["content"]
        return response_text


class Llava13b(BaseModel):
    def __init__(self, model_name, temperature):
        super().__init__(model_name, temperature)
        self.model = "yorickvp/llava-13b:e272157381e2a3bf12df3a8edd1f38d1dbd736bbb7437277c8b34175f8fce358"

    def generate_response(self, prompt_name, example_ids, image_path):
        prompt = prompts.get(prompt_name, {})
        instructions = prompt.get("instructions", None)

        response = replicate.run(
            self.model,
            input={
                "prompt": instructions,
                "image": open(image_path, "rb")
                },
        )
        response = list(response)
        response = ''.join(response)

        return response

class RandomPlayer(BaseModel):
    def generate_response(self, prompt_name, example_ids, image_path):
        actions = ["left", "right", "down", "drop", "turn right", "turn left"]
        return f"{{\"action\": \"{random.choice(actions)}\" }}"

class ManualPlayer(BaseModel):
    def generate_response(self, prompt_name, example_ids, image_path):
        return f"{{\"action\": \"{input('Enter your next move: ')}\" }}"


def get_model(model_name, temperature):
    models = {
        "gemini-pro-vision": GeminiProVision,
        "gpt-4-vision-preview": Gpt4VisionPreview,
        "llava-13b": Llava13b,
        "random": RandomPlayer,
        "manual": ManualPlayer
    }
    return models.get(model_name)(model_name, temperature)

def parse_response(prompt_name, response_text):
    print(response_text, "\n")

    prompt = prompts.get(prompt_name, {})
    action_type = prompt.get("action_type", None)

    stripped_text = response_text[
        response_text.index("{") : (response_text.index("}") + 1)
    ]
    data = eval(stripped_text)
    action = data.get("action", None)

    if "," in action:
        action_arr = action.split(",")
        stripped_action_arr = ( [action_arr[0].strip()] if action_type == 'single'
                            else [action.strip() for action in action_arr] )
    else:
        stripped_action_arr = [action]

    if len(stripped_action_arr) == 1:
        action = stripped_action_arr[0]
        if action not in ["down", "drop"]:
            stripped_action_arr = [action, "down"]
    return stripped_action_arr, stripped_text
