"""
Copilot Proxy Server - Routes requests through GitHub Copilot.

This server provides an OpenAI-compatible API endpoint that forwards requests
to GitHub Copilot using VS Code's language model API.

There are two ways to use Copilot:

1. **Direct CLI Mode** (Recommended): Use the GitHub Copilot CLI extension
   - Install: `gh extension install github/gh-copilot`
   - Authenticate: `gh auth login`
   - This script will use `gh copilot` commands directly

2. **VS Code Extension Mode**: Run this proxy while VS Code is open
   - Requires the GitHub Copilot extension in VS Code
   - Uses VS Code's internal API (more complex setup)

Usage:
    # Start the proxy server
    python copilot_proxy.py

    # Then set environment variables
    $env:LLM_PROVIDER = "copilot"
    $env:COPILOT_ENDPOINT = "http://localhost:11435"

    # Run the review
    python -m cli.main review --files your_file.py
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass

# Check for required packages
try:
    from aiohttp import web
except ImportError:
    print("Installing aiohttp...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
    from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("copilot_proxy")


@dataclass
class CopilotConfig:
    """Configuration for the Copilot proxy."""

    host: str = "localhost"
    port: int = 11435
    use_gh_cli: bool = True  # Use GitHub CLI for Copilot access
    timeout: int = 120  # Timeout in seconds


class CopilotProxy:
    """
    Proxy server that provides an OpenAI-compatible API using GitHub Copilot.
    """

    def __init__(self, config: CopilotConfig | None = None):
        self.config = config or CopilotConfig()
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Set up the API routes."""
        self.app.router.add_post("/v1/chat/completions", self.chat_completions)
        self.app.router.add_get("/v1/models", self.list_models)
        self.app.router.add_get("/health", self.health_check)

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "provider": "copilot"})

    async def list_models(self, request: web.Request) -> web.Response:
        """List available models (OpenAI-compatible endpoint)."""
        models = {
            "data": [
                {"id": "gpt-4", "object": "model", "owned_by": "github-copilot"},
                {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "github-copilot"},
                {"id": "copilot", "object": "model", "owned_by": "github-copilot"},
            ],
            "object": "list",
        }
        return web.json_response(models)

    async def chat_completions(self, request: web.Request) -> web.Response:
        """
        Handle chat completion requests (OpenAI-compatible endpoint).

        Forwards the request to GitHub Copilot via the gh CLI.
        """
        try:
            data = await request.json()
            messages = data.get("messages", [])

            # Build the prompt from messages
            prompt = self._build_prompt(messages)

            # Call Copilot
            if self.config.use_gh_cli:
                response_text = await self._call_copilot_cli(prompt)
            else:
                response_text = await self._call_copilot_vscode(prompt)

            # Format response in OpenAI format
            response = {
                "id": f"chatcmpl-copilot-{id(request)}",
                "object": "chat.completion",
                "created": int(asyncio.get_event_loop().time()),
                "model": data.get("model", "copilot"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(prompt) // 4,
                    "completion_tokens": len(response_text) // 4,
                    "total_tokens": (len(prompt) + len(response_text)) // 4,
                },
            }

            return web.json_response(response)

        except Exception as e:
            logger.exception(f"Error processing request: {e}")
            return web.json_response(
                {"error": {"message": str(e), "type": "server_error"}}, status=500
            )

    def _build_prompt(self, messages: list[dict]) -> str:
        """Build a prompt string from chat messages."""
        parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"System Instructions:\n{content}\n")
            elif role == "user":
                parts.append(f"User:\n{content}\n")
            elif role == "assistant":
                parts.append(f"Assistant:\n{content}\n")

        return "\n".join(parts)

    async def _call_copilot_cli(self, prompt: str) -> str:
        """
        Call GitHub Copilot using the gh CLI.

        Requires: gh extension install github/gh-copilot
        """
        try:
            # Write prompt to temp file to avoid shell escaping issues
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(prompt)
                prompt_file = f.name

            try:
                # Use gh copilot suggest for code-related queries
                process = await asyncio.create_subprocess_exec(
                    "gh",
                    "copilot",
                    "suggest",
                    "-t",
                    "shell",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode()), timeout=self.config.timeout
                )

                if process.returncode != 0:
                    # Fall back to explain command
                    process = await asyncio.create_subprocess_exec(
                        "gh",
                        "copilot",
                        "explain",
                        prompt[:500],  # Truncate for explain
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=self.config.timeout
                    )

                return stdout.decode("utf-8", errors="replace")

            finally:
                os.unlink(prompt_file)

        except FileNotFoundError:
            return await self._fallback_response(prompt)
        except asyncio.TimeoutError:
            return "Error: Request timed out. Please try again."
        except Exception as e:
            logger.error(f"Copilot CLI error: {e}")
            return await self._fallback_response(prompt)

    async def _call_copilot_vscode(self, prompt: str) -> str:
        """
        Call Copilot through VS Code's extension API.

        This is a placeholder - full implementation would require
        running inside VS Code's extension host.
        """
        return await self._fallback_response(prompt)

    async def _fallback_response(self, prompt: str) -> str:
        """
        Provide a fallback response when Copilot is not available.

        This analyzes the prompt and provides a structured response
        based on the code review format expected by the agents.
        """
        logger.warning("Copilot not available, using fallback analysis")

        # Parse what kind of review is being requested
        is_code_review = "review" in prompt.lower() or "analyze" in prompt.lower()

        if is_code_review:
            # Return a structured response indicating manual review needed
            return json.dumps(
                {
                    "findings": [
                        {
                            "category": "quality",
                            "severity": "info",
                            "title": "Manual Review Required",
                            "description": "GitHub Copilot is not available. Please ensure:\n"
                            "1. GitHub CLI is installed: `winget install GitHub.cli`\n"
                            "2. Copilot extension is installed: `gh extension install github/gh-copilot`\n"
                            "3. You are authenticated: `gh auth login`\n\n"
                            "Alternatively, set OPENAI_API_KEY or use Ollama for local models.",
                            "suggested_fix": "Run: gh extension install github/gh-copilot && gh auth login",
                        }
                    ],
                    "summary": "Copilot proxy is running but GitHub Copilot CLI is not configured.",
                },
                indent=2,
            )

        return "GitHub Copilot is not available. Please configure the CLI or use an alternative provider."

    def run(self):
        """Start the proxy server."""
        logger.info(f"Starting Copilot proxy on http://{self.config.host}:{self.config.port}")
        logger.info("Endpoints:")
        logger.info("  POST /v1/chat/completions - Chat completions (OpenAI-compatible)")
        logger.info("  GET  /v1/models - List models")
        logger.info("  GET  /health - Health check")
        logger.info("")
        logger.info("To use with agent-to-agent:")
        logger.info('  $env:LLM_PROVIDER = "copilot"')
        logger.info(f'  $env:COPILOT_ENDPOINT = "http://{self.config.host}:{self.config.port}"')

        web.run_app(self.app, host=self.config.host, port=self.config.port)


async def check_copilot_availability() -> dict:
    """Check if GitHub Copilot CLI is available and configured."""
    result = {
        "gh_cli_installed": False,
        "copilot_extension_installed": False,
        "authenticated": False,
        "ready": False,
    }

    # Check gh CLI
    try:
        process = await asyncio.create_subprocess_exec(
            "gh",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        if process.returncode == 0:
            result["gh_cli_installed"] = True
    except FileNotFoundError:
        pass

    if not result["gh_cli_installed"]:
        return result

    # Check Copilot extension
    try:
        process = await asyncio.create_subprocess_exec(
            "gh",
            "extension",
            "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        if b"copilot" in stdout.lower():
            result["copilot_extension_installed"] = True
    except Exception:
        pass

    # Check authentication
    try:
        process = await asyncio.create_subprocess_exec(
            "gh",
            "auth",
            "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _ = await process.communicate()
        if process.returncode == 0:
            result["authenticated"] = True
    except Exception:
        pass

    result["ready"] = all(
        [
            result["gh_cli_installed"],
            result["copilot_extension_installed"],
            result["authenticated"],
        ]
    )

    return result


def print_setup_instructions():
    """Print instructions for setting up Copilot."""
    print(
        """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GitHub Copilot Setup Instructions                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  1. Install GitHub CLI:                                                      ║
║     > winget install GitHub.cli                                              ║
║                                                                              ║
║  2. Authenticate with GitHub:                                                ║
║     > gh auth login                                                          ║
║                                                                              ║
║  3. Install Copilot extension:                                               ║
║     > gh extension install github/gh-copilot                                 ║
║                                                                              ║
║  4. Start this proxy server:                                                 ║
║     > python copilot_proxy.py                                                ║
║                                                                              ║
║  5. In another terminal, configure and run:                                  ║
║     > $env:LLM_PROVIDER = "copilot"                                          ║
║     > python -m cli.main review --files your_file.py                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GitHub Copilot Proxy Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=11435, help="Port to listen on")
    parser.add_argument("--check", action="store_true", help="Check Copilot availability")
    parser.add_argument("--setup", action="store_true", help="Show setup instructions")

    args = parser.parse_args()

    if args.setup:
        print_setup_instructions()
        sys.exit(0)

    if args.check:
        result = asyncio.run(check_copilot_availability())
        print("GitHub Copilot Status:")
        print(f"  GitHub CLI installed: {'✅' if result['gh_cli_installed'] else '❌'}")
        print(f"  Copilot extension:    {'✅' if result['copilot_extension_installed'] else '❌'}")
        print(f"  Authenticated:        {'✅' if result['authenticated'] else '❌'}")
        print(f"  Ready to use:         {'✅' if result['ready'] else '❌'}")

        if not result["ready"]:
            print("\nRun 'python copilot_proxy.py --setup' for installation instructions.")

        sys.exit(0 if result["ready"] else 1)

    # Start the proxy server
    config = CopilotConfig(host=args.host, port=args.port)
    proxy = CopilotProxy(config)
    proxy.run()
