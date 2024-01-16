def check_if_valid_json(response_text):
    try:
        stripped_text = response_text[
            response_text.index("{") : (response_text.index("}") + 1)
        ]
        eval(stripped_text)
        return True
    except:
        return False