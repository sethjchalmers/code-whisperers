/**
 * Code Whisperers - Copilot Bridge Extension
 *
 * This extension exposes GitHub Copilot's language models as an OpenAI-compatible
 * HTTP API endpoint, allowing the Code Whisperers CLI tool to use your Copilot
 * subscription for AI-powered code reviews.
 *
 * @author sethjchalmers
 * @license MIT
 */

import * as vscode from "vscode";
import * as http from "http";

// Extension state
let server: http.Server | null = null;
let statusBarItem: vscode.StatusBarItem;
let outputChannel: vscode.OutputChannel;

/**
 * Activate the extension
 */
export function activate(context: vscode.ExtensionContext): void {
  outputChannel = vscode.window.createOutputChannel("Code Whisperers Bridge");
  log("Extension activating...");

  // Create status bar item
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.command = "codeWhisperers.showStatus";
  context.subscriptions.push(statusBarItem);

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand("codeWhisperers.startBridge", startBridge),
    vscode.commands.registerCommand("codeWhisperers.stopBridge", stopBridge),
    vscode.commands.registerCommand("codeWhisperers.showStatus", showStatus)
  );

  // Auto-start if configured
  const config = vscode.workspace.getConfiguration("codeWhisperers.bridge");
  if (config.get<boolean>("autoStart", true)) {
    startBridge();
  }

  log("Extension activated successfully");
}

/**
 * Deactivate the extension
 */
export function deactivate(): void {
  stopBridge();
  outputChannel?.dispose();
}

/**
 * Log a message to the output channel
 */
function log(message: string): void {
  const timestamp = new Date().toISOString();
  outputChannel.appendLine(`[${timestamp}] ${message}`);
}

/**
 * Start the Copilot Bridge HTTP server
 */
async function startBridge(): Promise<void> {
  if (server) {
    vscode.window.showInformationMessage(
      "Code Whisperers Bridge is already running"
    );
    return;
  }

  const config = vscode.workspace.getConfiguration("codeWhisperers.bridge");
  const port = config.get<number>("port", 11435);

  // Check if Copilot is available
  const models = await getAvailableModels();
  if (models.length === 0) {
    vscode.window.showErrorMessage(
      "GitHub Copilot is not available. Please ensure you have Copilot Chat installed and are signed in."
    );
    return;
  }

  log(`Available Copilot models: ${models.map((m) => m.id).join(", ")}`);

  server = http.createServer(async (req, res) => {
    // Set CORS headers
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

    if (req.method === "OPTIONS") {
      res.writeHead(200);
      res.end();
      return;
    }

    try {
      await handleRequest(req, res);
    } catch (error) {
      log(`Error handling request: ${error}`);
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: { message: String(error) } }));
    }
  });

  server.listen(port, "127.0.0.1", () => {
    log(`Bridge server started on http://127.0.0.1:${port}`);
    vscode.window.showInformationMessage(
      `Code Whisperers Bridge started on port ${port}`
    );
    updateStatusBar(true, port);
  });

  server.on("error", (error: NodeJS.ErrnoException) => {
    if (error.code === "EADDRINUSE") {
      vscode.window.showErrorMessage(
        `Port ${port} is already in use. Please configure a different port.`
      );
    } else {
      vscode.window.showErrorMessage(`Bridge server error: ${error.message}`);
    }
    log(`Server error: ${error}`);
    server = null;
    updateStatusBar(false);
  });
}

/**
 * Stop the Copilot Bridge HTTP server
 */
function stopBridge(): void {
  if (server) {
    server.close();
    server = null;
    log("Bridge server stopped");
    vscode.window.showInformationMessage("Code Whisperers Bridge stopped");
    updateStatusBar(false);
  }
}

/**
 * Show the current bridge status
 */
async function showStatus(): Promise<void> {
  const models = await getAvailableModels();
  const config = vscode.workspace.getConfiguration("codeWhisperers.bridge");
  const port = config.get<number>("port", 11435);

  const status = server ? "🟢 Running" : "🔴 Stopped";
  const modelList =
    models.length > 0
      ? models.map((m) => `  • ${m.id} (${m.vendor})`).join("\n")
      : "  No models available";

  const message = `Code Whisperers Copilot Bridge

Status: ${status}
Port: ${port}
Endpoint: http://127.0.0.1:${port}/v1/chat/completions

Available Models:
${modelList}

Usage:
  export LLM_PROVIDER=copilot
  export COPILOT_ENDPOINT=http://127.0.0.1:${port}
  python -m cli.main review --diff HEAD~1`;

  const action = await vscode.window.showInformationMessage(
    message,
    { modal: true },
    server ? "Stop Bridge" : "Start Bridge",
    "Copy Endpoint"
  );

  if (action === "Stop Bridge") {
    stopBridge();
  } else if (action === "Start Bridge") {
    startBridge();
  } else if (action === "Copy Endpoint") {
    await vscode.env.clipboard.writeText(`http://127.0.0.1:${port}`);
    vscode.window.showInformationMessage("Endpoint copied to clipboard");
  }
}

/**
 * Update the status bar item
 */
function updateStatusBar(running: boolean, port?: number): void {
  if (running && port) {
    statusBarItem.text = `$(symbol-event) CW Bridge :${port}`;
    statusBarItem.tooltip = `Code Whisperers Copilot Bridge running on port ${port}`;
    statusBarItem.backgroundColor = undefined;
  } else {
    statusBarItem.text = "$(symbol-event) CW Bridge";
    statusBarItem.tooltip = "Code Whisperers Copilot Bridge (stopped)";
    statusBarItem.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.warningBackground"
    );
  }
  statusBarItem.show();
}

/**
 * Get available Copilot language models
 */
async function getAvailableModels(): Promise<vscode.LanguageModelChat[]> {
  try {
    // Select all available chat models from Copilot
    const models = await vscode.lm.selectChatModels({
      vendor: "copilot",
    });
    return models;
  } catch (error) {
    log(`Error getting models: ${error}`);
    return [];
  }
}

/**
 * Handle incoming HTTP requests
 */
async function handleRequest(
  req: http.IncomingMessage,
  res: http.ServerResponse
): Promise<void> {
  const url = req.url || "/";

  log(`${req.method} ${url}`);

  // Health check
  if (url === "/health" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        status: "healthy",
        provider: "copilot",
        models: (await getAvailableModels()).map((m) => m.id),
      })
    );
    return;
  }

  // List models (OpenAI-compatible)
  if (url === "/v1/models" && req.method === "GET") {
    const models = await getAvailableModels();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        object: "list",
        data: models.map((m) => ({
          id: m.id,
          object: "model",
          owned_by: m.vendor,
          permission: [],
        })),
      })
    );
    return;
  }

  // Chat completions (OpenAI-compatible)
  if (url === "/v1/chat/completions" && req.method === "POST") {
    await handleChatCompletion(req, res);
    return;
  }

  // 404 for unknown routes
  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: { message: "Not found" } }));
}

/**
 * Handle chat completion requests
 */
async function handleChatCompletion(
  req: http.IncomingMessage,
  res: http.ServerResponse
): Promise<void> {
  // Parse request body
  const body = await parseRequestBody(req);
  const { messages, model: requestedModel } = body;
  // Note: body.stream is available for future streaming support

  if (!messages || !Array.isArray(messages)) {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: { message: "messages array is required" } }));
    return;
  }

  // Get available models
  const models = await getAvailableModels();
  if (models.length === 0) {
    res.writeHead(503, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        error: { message: "No Copilot models available. Is Copilot signed in?" },
      })
    );
    return;
  }

  // Select the best model
  const config = vscode.workspace.getConfiguration("codeWhisperers.bridge");
  const preferredModel = config.get<string>("preferredModel", "gpt-4o") ?? "gpt-4o";

  let selectedModel = models.find(
    (m) =>
      (requestedModel && m.id.includes(requestedModel)) ||
      m.id.includes(preferredModel)
  );
  if (!selectedModel) {
    selectedModel = models[0]; // Fall back to first available
  }

  log(`Using model: ${selectedModel.id}`);

  // Convert messages to VS Code format
  const vsCodeMessages: vscode.LanguageModelChatMessage[] = messages.map(
    (msg: ChatMessage) => {
      if (msg.role === "system" || msg.role === "user") {
        return vscode.LanguageModelChatMessage.User(msg.content);
      } else {
        return vscode.LanguageModelChatMessage.Assistant(msg.content);
      }
    }
  );

  try {
    // Create a cancellation token source with timeout
    const cancellationSource = new vscode.CancellationTokenSource();
    const config = vscode.workspace.getConfiguration("codeWhisperers.bridge");
    const timeoutMs = config.get<number>("requestTimeout", 120000); // Default 2 minutes

    const timeoutHandle = setTimeout(() => {
      cancellationSource.cancel();
    }, timeoutMs);

    try {
      // Make the request to Copilot
      const response = await selectedModel.sendRequest(
        vsCodeMessages,
        {},
        cancellationSource.token
      );

      // Collect the response
      let responseText = "";
      for await (const chunk of response.text) {
        responseText += chunk;
      }

      clearTimeout(timeoutHandle);
      log(`Response received: ${responseText.length} characters`);

    // Send OpenAI-compatible response
    const promptTokens = Math.ceil(
      messages.reduce((acc: number, m: ChatMessage) => acc + m.content.length / 4, 0)
    );
    const completionTokens = Math.ceil(responseText.length / 4);

    const openAIResponse = {
      id: `chatcmpl-${Date.now()}`,
      object: "chat.completion",
      created: Math.floor(Date.now() / 1000),
      model: selectedModel.id,
      choices: [
        {
          index: 0,
          message: {
            role: "assistant",
            content: responseText,
          },
          finish_reason: "stop",
        },
      ],
      usage: {
        prompt_tokens: promptTokens,
        completion_tokens: completionTokens,
        total_tokens: promptTokens + completionTokens,
      },
    };

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(openAIResponse));
    } finally {
      cancellationSource.dispose();
    }
  } catch (error) {
    log(`Copilot request error: ${error}`);

    // Check for specific error types
    if (error instanceof vscode.LanguageModelError) {
      if (error.code === vscode.LanguageModelError.NotFound.name) {
        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: { message: "Model not found" } }));
        return;
      }
      if (error.code === vscode.LanguageModelError.NoPermissions.name) {
        res.writeHead(403, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            error: {
              message:
                "Permission denied. Please accept the Copilot terms in VS Code.",
            },
          })
        );
        return;
      }
    }

    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: { message: String(error) } }));
  }
}

/**
 * Parse the request body as JSON
 */
function parseRequestBody(req: http.IncomingMessage): Promise<ChatCompletionRequest> {
  return new Promise((resolve, reject) => {
    let body = "";
    const maxBodySize = 10 * 1024 * 1024; // 10MB limit
    let bodySize = 0;

    req.on("data", (chunk: Buffer) => {
      bodySize += chunk.length;
      if (bodySize > maxBodySize) {
        req.destroy();
        reject(new Error("Request body too large"));
        return;
      }
      body += chunk.toString();
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body) as ChatCompletionRequest);
      } catch {
        reject(new Error("Invalid JSON in request body"));
      }
    });
    req.on("error", reject);
  });
}

/**
 * Types for request/response handling
 */
interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ChatCompletionRequest {
  messages: ChatMessage[];
  model?: string;
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
}
