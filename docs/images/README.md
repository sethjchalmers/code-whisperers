# Architecture Diagram Placeholder

Since this is a text-based placeholder, here's the architecture in ASCII art:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent-to-Agent Code Review Pipeline                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI / API                                   │
│                         (cli/main.py)                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │     Git      │  │   Review     │  │   Config     │
         │ Integration  │  │   Pipeline   │  │  Settings    │
         └──────────────┘  └──────────────┘  └──────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Expert Agents                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │Terraform │ │  GitOps  │ │ Jenkins  │ │  Python  │ │ Security │      │
│  │  Expert  │ │  Expert  │ │  Expert  │ │  Expert  │ │  Expert  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐                                              │
│  │   Cost   │ │  Clean   │                                              │
│  │  Expert  │ │   Code   │                                              │
│  └──────────┘ └──────────┘                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          LLM Providers                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  GitHub  │ │  Ollama  │ │  OpenAI  │ │  Azure   │ │  Copilot │      │
│  │  Models  │ │ (Local)  │ │   API    │ │  OpenAI  │ │  Proxy   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

## To add a proper image:

1. Create an architecture diagram using:
   - [Excalidraw](https://excalidraw.com/)
   - [draw.io](https://draw.io/)
   - [Mermaid](https://mermaid.js.org/)

2. Export as PNG and save to `docs/images/architecture.png`

3. The README will automatically display it.
