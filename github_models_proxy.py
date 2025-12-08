"""
GitHub Models Proxy - Use GitHub's free AI models API.

GitHub provides free access to various AI models through their API:
- Claude models (Anthropic)
- GPT models (OpenAI)
- Llama models (Meta)
- And more

This proxy provides an OpenAI-compatible endpoint using GitHub's Models API.

Usage:
    # Start the proxy server
    python github_models_proxy.py

    # Then configure environment
    $env:LLM_PROVIDER = "copilot"
    $env:COPILOT_ENDPOINT = "http://localhost:11435"

    # Run the review
    python -m cli.main review --files your_file.py
"""

import asyncio
import logging
import os
import subprocess
import sys

# Check for required packages
try:
    import aiohttp
    from aiohttp import web
except ImportError:
    print("Installing aiohttp...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
    import aiohttp
    from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github_models_proxy")

# GitHub Models API endpoint (Azure-hosted)
GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"


class GitHubModelsProxy:
    """
    Proxy server that provides an OpenAI-compatible API using GitHub Models.
    """

    def __init__(self, host: str = "localhost", port: int = 11435):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.github_token = self._get_github_token()
        self._setup_routes()

    def _get_github_token(self) -> str:
        """Get GitHub token from environment or gh CLI."""
        # Try environment variable first
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            return token

        # Try gh CLI
        try:
            result = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        raise RuntimeError(
            "No GitHub token found. Please either:\n"
            "1. Set GITHUB_TOKEN environment variable\n"
            "2. Run 'gh auth login' to authenticate"
        )

    def _setup_routes(self):
        """Set up the API routes."""
        self.app.router.add_post("/v1/chat/completions", self.chat_completions)
        self.app.router.add_get("/v1/models", self.list_models)
        self.app.router.add_get("/health", self.health_check)

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response(
            {"status": "healthy", "provider": "github-models", "has_token": bool(self.github_token)}
        )

    async def list_models(self, request: web.Request) -> web.Response:
        """List available models."""
        models = {
            "data": [
                {"id": "gpt-4o", "object": "model", "owned_by": "azure-openai"},
                {"id": "gpt-4o-mini", "object": "model", "owned_by": "azure-openai"},
                {"id": "Meta-Llama-3.1-405B-Instruct", "object": "model", "owned_by": "meta"},
                {"id": "Meta-Llama-3.1-70B-Instruct", "object": "model", "owned_by": "meta"},
                {"id": "Meta-Llama-3.1-8B-Instruct", "object": "model", "owned_by": "meta"},
                {"id": "Mistral-large-2407", "object": "model", "owned_by": "mistralai"},
                {"id": "Mistral-Nemo", "object": "model", "owned_by": "mistralai"},
            ],
            "object": "list",
        }
        return web.json_response(models)

    async def chat_completions(self, request: web.Request) -> web.Response:
        """
        Handle chat completion requests (OpenAI-compatible endpoint).

        Forwards the request to GitHub Models API.
        """
        try:
            data = await request.json()

            # Map model names to GitHub Models format
            model = data.get("model", "gpt-4o")
            model_mapping = {
                # OpenAI models
                "gpt-4": "gpt-4o",
                "gpt-4-turbo": "gpt-4o",
                "gpt-4-turbo-preview": "gpt-4o",
                "gpt-4o": "gpt-4o",
                "gpt-4o-mini": "gpt-4o-mini",
                "gpt-3.5-turbo": "gpt-4o-mini",
                # Claude -> use GPT-4o (best available)
                "claude-sonnet-4-20250514": "gpt-4o",
                "claude-3-sonnet": "gpt-4o",
                "claude-3-opus": "gpt-4o",
                # Llama models
                "llama3.1": "Meta-Llama-3.1-70B-Instruct",
                "llama3": "Meta-Llama-3.1-70B-Instruct",
                # Mistral
                "mistral": "Mistral-large-2407",
                "mistral-large": "Mistral-large-2407",
            }
            model = model_mapping.get(model, model)

            # Forward to GitHub Models API
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": data.get("messages", []),
                "temperature": data.get("temperature", 0.1),
                "max_tokens": data.get("max_tokens", 4096),
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{GITHUB_MODELS_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GitHub Models API error: {response.status} - {error_text}")
                        return web.json_response(
                            {"error": {"message": error_text, "type": "api_error"}},
                            status=response.status,
                        )

                    result = await response.json()
                    return web.json_response(result)

        except asyncio.TimeoutError:
            return web.json_response(
                {"error": {"message": "Request timed out", "type": "timeout_error"}}, status=504
            )
        except Exception as e:
            logger.exception(f"Error processing request: {e}")
            return web.json_response(
                {"error": {"message": str(e), "type": "server_error"}}, status=500
            )

    def run(self):
        """Start the proxy server."""
        logger.info(f"Starting GitHub Models proxy on http://{self.host}:{self.port}")
        logger.info(f"GitHub token: {'✓ Found' if self.github_token else '✗ Missing'}")
        logger.info("")
        logger.info("Available models (free via GitHub):")
        logger.info("  - gpt-4o (OpenAI GPT-4o)")
        logger.info("  - gpt-4o-mini (OpenAI GPT-4o mini)")
        logger.info("  - Meta-Llama-3.1-405B-Instruct (Llama 3.1 405B)")
        logger.info("  - Meta-Llama-3.1-70B-Instruct (Llama 3.1 70B)")
        logger.info("  - Mistral-large-2407 (Mistral Large)")
        logger.info("")
        logger.info("Note: Claude is not available on GitHub Models.")
        logger.info("      Requests for Claude will use GPT-4o instead.")
        logger.info("")
        logger.info("To use with agent-to-agent:")
        logger.info('  $env:LLM_PROVIDER = "copilot"')
        logger.info('  $env:LLM_MODEL = "gpt-4o"')

        web.run_app(self.app, host=self.host, port=self.port, print=None)


if __name__ == "__main__":
    proxy = GitHubModelsProxy()
    proxy.run()
