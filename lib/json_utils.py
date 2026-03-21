import re


def strip_markdown_fences(text):
    """Strip markdown code fences (```json ... ```) from response text."""
    return re.sub(r"```(?:json)?\s*\n?", "", text).strip()


def extract_json_object(text):
    """Extract the outermost JSON object from text."""
    text = strip_markdown_fences(text)
    start = text.index("{")
    end = text.rindex("}") + 1
    return text[start:end]


def check_if_valid_json(response_text):
    try:
        stripped_text = extract_json_object(response_text)
        json_parsed = eval(stripped_text)
        if not isinstance(json_parsed["action"], str):
            return False
        return True
    except:
        return False
