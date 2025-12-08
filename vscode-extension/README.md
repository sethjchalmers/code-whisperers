# Code Whisperers - Copilot Bridge Extension

A VS Code extension that exposes GitHub Copilot's language models as an OpenAI-compatible HTTP API endpoint, allowing the Code Whisperers CLI tool to use your Copilot subscription for AI-powered code reviews.

## Features

- 🔌 **OpenAI-Compatible API**: Exposes `/v1/chat/completions` and `/v1/models` endpoints
- 🚀 **Auto-Start**: Automatically starts the bridge server when VS Code opens
- 🎯 **Model Selection**: Automatically selects the best available Copilot model
- 📊 **Status Bar**: Shows bridge status in the VS Code status bar
- 🔒 **Localhost Only**: Server only listens on 127.0.0.1 for security

## Requirements

- VS Code 1.90.0 or later
- GitHub Copilot Chat extension installed and signed in
- Active GitHub Copilot subscription

## Installation

### From VSIX (Local)

```bash
cd vscode-extension
npm install
npm run compile
npx vsce package
code --install-extension code-whisperers-copilot-bridge-1.0.0.vsix
```

### From Marketplace (Coming Soon)

Search for "Code Whisperers Copilot Bridge" in the VS Code Extensions view.

## Usage

### 1. Start the Bridge

The bridge starts automatically when VS Code opens. You can also:

- Use Command Palette: `Code Whisperers: Start Copilot Bridge Server`
- Click the status bar item: `CW Bridge`

### 2. Configure the CLI

Set environment variables:

```bash
# Linux/macOS
export LLM_PROVIDER=copilot
export COPILOT_ENDPOINT=http://127.0.0.1:11435

# Windows PowerShell
$env:LLM_PROVIDER = "copilot"
$env:COPILOT_ENDPOINT = "http://127.0.0.1:11435"
```

### 3. Run Code Reviews

```bash
# Review last commit
python -m cli.main review --diff HEAD~1

# Review vs main branch
python -m cli.main review --base main

# Review specific files
python -m cli.main review --files src/*.py
```

## Configuration

| Setting                                | Default  | Description                    |
| -------------------------------------- | -------- | ------------------------------ |
| `codeWhisperers.bridge.port`           | `11435`  | HTTP server port               |
| `codeWhisperers.bridge.autoStart`      | `true`   | Start server on VS Code launch |
| `codeWhisperers.bridge.preferredModel` | `gpt-4o` | Preferred Copilot model        |

## API Endpoints

| Endpoint               | Method | Description                        |
| ---------------------- | ------ | ---------------------------------- |
| `/v1/chat/completions` | POST   | OpenAI-compatible chat completions |
| `/v1/models`           | GET    | List available models              |
| `/health`              | GET    | Health check                       |

## Commands

| Command                                        | Description                      |
| ---------------------------------------------- | -------------------------------- |
| `Code Whisperers: Start Copilot Bridge Server` | Start the HTTP server            |
| `Code Whisperers: Stop Copilot Bridge Server`  | Stop the HTTP server             |
| `Code Whisperers: Show Bridge Status`          | Show status and available models |

## Troubleshooting

### "No Copilot models available"

- Ensure GitHub Copilot Chat extension is installed
- Sign in to GitHub Copilot (click Copilot icon in status bar)
- Accept any terms/permissions prompts

### "Port already in use"

Change the port in settings:

```json
{
  "codeWhisperers.bridge.port": 11436
}
```

### "Permission denied"

When first using the bridge, VS Code may prompt you to allow the extension to use Copilot. Click "Allow" to grant permission.

## Development

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch for changes
npm run watch

# Package extension
npm run package
```

## License

MIT - See [LICENSE](../LICENSE)
