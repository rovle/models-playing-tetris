class ModelCallError(Exception):
    """A model call failed and is worth retrying.

    Backends that skip litellm raise this, so the retry loop in ``run_model``
    can catch every backend the same way.
    """
