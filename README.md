# Home Assistant OpencodeZen

![GitHub Repo stars](https://img.shields.io/github/stars/McTalian/hacs-opencode-zen?style=for-the-badge&color=%23AFB0CC)
![GitHub Release](https://img.shields.io/github/v/release/McTalian/hacs-opencode-zen?style=for-the-badge&color=%231CB00A)

Integration for [OpencodeZen API](https://opencode.ai/zen) — adds an AI conversation agent and AI task agent to Home Assistant. Powered by [opencode.ai](https://opencode.ai).

Build custom LLM-powered automations, voice assistants, and data generation tasks using models served through the OpencodeZen API. Supports tool/function calling, structured JSON output, web search, and image/PDF attachments.

## Features

- **Conversation Agent** — AI assistant for Home Assistant's conversation/assist pipeline. Can control devices, query state, and run automations via tool calling.
- **AI Task Agent** — Generate structured data from AI prompts (JSON schema output). Useful for automations that need AI-generated data.
- **Multiple agents** — Add multiple conversation or task agents, each with its own model and configuration.
- **Web search** — Toggle per agent. Appends `:online` suffix to model name.
- **File attachments** — Images and PDFs supported.
- **Custom prompt** — Configure system prompt per agent.

## Prerequisites

You need an OpencodeZen API key from [opencode.ai](https://opencode.ai).

## Installation

1. Add this repository to HACS as a custom repository.
2. Install OpencodeZen via HACS.
3. Restart Home Assistant.
4. Go to Settings → Devices & services → Add integration → Search for "OpencodeZen".
5. Enter your API key.

### Adding a conversation agent

After setup, use the configure button on the integration entry to add a conversation agent subentry. Select model, optionally configure prompt, enable tool access and web search.

### Adding an AI task agent

Use the configure button and select "AI Task" subentry type. Choose a model that supports structured outputs.

## Configuration options

| Option | Description |
|--------|-------------|
| Model | AI model to use |
| Prompt | Custom system prompt |
| Tool access | Allow agent to call Home Assistant APIs |
| Web search | Enable web search for this agent |

## Supported models

All models available through the OpencodeZen API that support chat completions. See [opencode.ai/models](https://opencode.ai/models) for available models.

## License

GPL-3.0
