def check_if_valid_json(response_text):
    try:
        stripped_text = response_text[
            response_text.index("{") : (response_text.index("}") + 1)
        ]
        json_parsed = eval(stripped_text)
        if not isinstance(json_parsed["action"], str):
            return False
        return True
    except:
        return False