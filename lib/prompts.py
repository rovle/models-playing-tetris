"""Load prompts from ``assets/prompts/<name>.md``: YAML frontmatter for metadata,
body for instructions. Filename (without extension) is the ``--prompt_name`` value.
"""

from pathlib import Path

import frontmatter


def load_prompts(directory: str | Path) -> dict[str, dict]:
    """Return ``{prompt_name: {action_type, instructions, ...}}`` for every .md file."""
    prompts: dict[str, dict] = {}
    for path in Path(directory).glob("*.md"):
        prompt = frontmatter.load(str(path))
        prompts[path.stem] = {**prompt.metadata, "instructions": prompt.content}
    return prompts
