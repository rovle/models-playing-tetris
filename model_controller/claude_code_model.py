"""Play through the Claude Code CLI instead of the Anthropic API.

Each move runs one `claude -p` subprocess: the prompt goes in on stdin, a JSON
stream comes back. The bill goes to whatever account the CLI is logged in with,
so a subscription can be used instead of API credits.

The CLI is started as plainly as possible: no tools, no project files, no
settings, and our prompt in place of its own. See
`docs/claude_code_backend.md` for what that does and does not guarantee.
"""

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

from model_controller.errors import ModelCallError
from model_controller.prompt_builder import (
    build_request,
    log_full_prompt,
    to_anthropic_content,
)

CLAUDE_CODE_PREFIX = "claude-code/"
DEFAULT_TIMEOUT_S = 900

# Removed from the subprocess environment so the CLI cannot charge an API key
# instead of the subscription. Loading .env usually sets these.
BLOCKED_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
)


def _clean_env():
    env = {k: v for k, v in os.environ.items() if k not in BLOCKED_ENV_VARS}
    # Labels these runs in the CLI's own logs.
    env["CLAUDE_CODE_ENTRYPOINT"] = "tetris-benchmark"
    return env


def _parse_stream(stdout):
    """Return the JSON objects from a stream-json stdout."""
    messages = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return messages


def _collect_thinking(messages):
    parts = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        for block in msg.get("message", {}).get("content", []):
            if block.get("type") == "thinking" and block.get("thinking"):
                parts.append(block["thinking"])
    return "\n".join(parts) or None


def _collect_assistant_text(messages):
    parts = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        for block in msg.get("message", {}).get("content", []):
            if block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])
    return "\n".join(parts)


class ClaudeCodeModel:
    """Same interface as ``LiteLLMModel``, backed by the Claude Code CLI.

    There is no temperature setting because the CLI has no flag for it.
    """

    def __init__(
        self,
        model_name,
        prompts,
        examples,
        effort=None,
        cli_path="claude",
        timeout=DEFAULT_TIMEOUT_S,
    ):
        self.model_name = model_name
        self.cli_model = model_name[len(CLAUDE_CODE_PREFIX) :] or "opus"
        self.prompts = prompts
        self.examples = examples
        self.effort = effort
        self.cli_path = shutil.which(cli_path) or cli_path
        self.timeout = timeout
        self.last_metrics = {}
        # What a name like "opus" turned out to mean. Filled in on the first call.
        self.resolved_model = None
        self._prompt_logged = False
        self._auth_checked = False
        # Running from an empty directory keeps this repo's CLAUDE.md, memory
        # and git status out of the model's context.
        self._workdir = tempfile.mkdtemp(prefix="tetris-claude-code-")
        atexit.register(shutil.rmtree, self._workdir, True)

    def _command(self, instructions):
        cmd = [
            self.cli_path,
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.cli_model,
            "--system-prompt",
            instructions,
            "--tools",
            "",
            "--safe-mode",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--no-session-persistence",
            "--disable-slash-commands",
            # Naming the session saves a second model call, which the CLI would
            # otherwise spend inventing a title.
            "--name",
            "tetris-benchmark",
        ]
        if self.effort:
            cmd += ["--effort", self.effort]
        return cmd

    def _read_init(self, messages):
        """Note which model actually ran, and warn once if the CLI is charging an
        API key instead of the subscription."""
        for msg in messages:
            if msg.get("type") != "system" or msg.get("subtype") != "init":
                continue
            self.resolved_model = msg.get("model") or self.resolved_model
            if self._auth_checked:
                return
            self._auth_checked = True
            source = msg.get("apiKeySource")
            if source and source != "none":
                print(
                    f"[CLAUDE-CODE] warning: apiKeySource={source}, so this run "
                    "is not billed to a subscription"
                )
            if self.resolved_model and self.resolved_model != self.cli_model:
                print(
                    f"[CLAUDE-CODE] '{self.cli_model}' resolved to {self.resolved_model}"
                )
            return

    def _log_rate_limit(self, messages):
        """Report any quota window that is running out.

        The CLI tracks several windows (five_hour, seven_day, seven_day_opus).
        A healthy one reports "allowed", then "allowed_warning" near the cap,
        then "rejected". Only the last two are worth printing.
        """
        for msg in messages:
            if msg.get("type") != "rate_limit_event":
                continue
            info = msg.get("rate_limit_info") or {}
            status = info.get("status")
            if not status or status == "allowed":
                continue
            resets_at = info.get("resetsAt")
            when = (
                datetime.fromtimestamp(resets_at).strftime("%H:%M:%S")
                if resets_at
                else "unknown"
            )
            print(
                f"[CLAUDE-CODE] {info.get('rateLimitType')} quota {status}, "
                f"resets at {when}",
                flush=True,
            )

    def generate_response(self, prompt_name, example_ids, image_path):
        instructions, blocks, _ = build_request(
            self.prompts.get(prompt_name, {}), self.examples, example_ids, image_path
        )
        if not self._prompt_logged:
            log_full_prompt(instructions, blocks)
            self._prompt_logged = True

        payload = {
            "type": "user",
            "message": {"role": "user", "content": to_anthropic_content(blocks)},
        }

        started = time.monotonic()
        try:
            proc = subprocess.run(
                self._command(instructions),
                input=json.dumps(payload) + "\n",
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self._workdir,
                env=_clean_env(),
            )
        except subprocess.TimeoutExpired:
            raise ModelCallError(f"claude CLI timed out after {self.timeout}s")
        except FileNotFoundError:
            raise ModelCallError(
                f"claude CLI not found at {self.cli_path}; install it or pass a valid path"
            )
        duration_ms = int((time.monotonic() - started) * 1000)

        messages = _parse_stream(proc.stdout)
        self._read_init(messages)
        self._log_rate_limit(messages)

        if proc.returncode != 0:
            raise ModelCallError(
                f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[-500:]}"
            )

        result = next((m for m in messages if m.get("type") == "result"), None)
        if result is None:
            raise ModelCallError("claude CLI produced no result message")
        if result.get("is_error") or result.get("subtype") != "success":
            raise ModelCallError(
                f"claude CLI returned {result.get('subtype')}: "
                f"{str(result.get('result'))[:500]}"
            )

        text = result.get("result") or _collect_assistant_text(messages)
        reasoning = _collect_thinking(messages)
        if reasoning:
            print(f"[REASONING] {reasoning}")

        usage = result.get("usage", {})
        cached = usage.get("cache_read_input_tokens", 0)
        created = usage.get("cache_creation_input_tokens", 0)
        if cached or created:
            print(f"[CACHE] read={cached} write={created}")

        self.last_metrics = {
            "backend": "claude-code",
            "model": self.cli_model,
            "resolved_model": self.resolved_model,
            "effort": self.effort,
            "duration_ms": duration_ms,
            "duration_api_ms": result.get("duration_api_ms"),
            "ttft_ms": result.get("ttft_ms"),
            "usage": usage,
            "total_cost_usd": result.get("total_cost_usd"),
            "session_id": result.get("session_id"),
        }
        sys.stdout.flush()

        return text, reasoning
