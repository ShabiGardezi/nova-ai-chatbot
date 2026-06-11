# Nova · AI Chatbot

A production-quality AI chatbot with both a **command-line** and a **modern web** interface, built on a clean, typed Python service layer.

The web UI is a lightweight, ChatGPT/Claude-inspired product: dark-mode, glassmorphism, real-time streaming, and conversation history — designed to feel like a real AI startup app.

> Provider-agnostic: works with any OpenAI-compatible API (OpenAI, **Groq**, OpenRouter, Ollama, …).

---

## Features

- **Two interfaces** — interactive CLI (`app.py`) and a FastAPI web app (`server.py`) over a shared core.
- **Streaming responses** — tokens render as they arrive, in both the CLI and the browser.
- **Conversation memory** — context is preserved across turns, with a configurable window.
- **SQLite persistence** — conversations and messages saved via SQLAlchemy; list, resume, and delete.
- **Token usage + cost** — prompt/completion/total tokens with a configurable cost estimate.
- **Personalities** — General Assistant, Software Architect, and Interview Coach.
- **Premium UI** — animated gradient logo, floating particles, AI thinking indicator, live stats panel, token/message badges, smooth transitions, and a pure-CSS empty-state illustration.
- **Clean architecture** — small, single-responsibility modules with full type hints.

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, OpenAI SDK, SQLAlchemy
- **Frontend:** Semantic HTML, modern CSS (variables, glassmorphism), vanilla JS (ES modules) — no frameworks, no CDNs
- **Storage:** SQLite (any SQLAlchemy URL)

---

## Project Structure

```
ai-chatbot/
├── app.py            # CLI entry point
├── server.py         # FastAPI app (REST + SSE streaming + static)
├── chatbot.py        # Chatbot service (OpenAI client + memory + persistence)
├── config.py         # Env-based configuration (validated)
├── memory.py         # Conversation memory window
├── prompts.py        # System prompt + selectable personalities
├── storage.py        # SQLAlchemy models + ConversationStore repository
├── usage.py          # Token usage + cost estimation
├── frontend/
│   ├── index.html    # App shell
│   ├── styles.css    # Dark theme, glassmorphism, animations
│   └── app.js         # Streaming, state, rendering (vanilla JS)
├── requirements.txt
└── .env.example
```

---

## Getting Started

### 1. Clone & create a virtual environment

```bash
git clone https://github.com/ShabiGardezi/nova-ai-chatbot.git
cd nova-ai-chatbot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> Requires Python 3.12+.

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your API key. For a **free** option, sign up at [Groq](https://console.groq.com/keys) and use:

```env
OPENAI_API_KEY=gsk_your_groq_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
```

### 3. Run

**Web app:**

```bash
uvicorn server:app --reload
# open http://127.0.0.1:8000
```

**CLI:**

```bash
python app.py
```

CLI commands: `list`, `resume <id>`, `delete <id>`, `new`, `clear`, `exit`.

---

## Configuration

All settings are read from the environment (see `.env.example`):

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | _(required)_ | API key for the chosen provider. |
| `OPENAI_BASE_URL` | _(OpenAI default)_ | OpenAI-compatible endpoint (e.g. Groq). |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model id. |
| `OPENAI_TEMPERATURE` | `0.7` | Sampling temperature. |
| `MAX_HISTORY_MESSAGES` | `20` | Messages kept in context. |
| `PROMPT_COST_PER_1K` | `0.0` | Prompt token price (cost estimate). |
| `COMPLETION_COST_PER_1K` | `0.0` | Completion token price (cost estimate). |
| `DATABASE_URL` | `sqlite:///chatbot.db` | SQLAlchemy database URL. |

---

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/meta` | Model + available personalities. |
| `POST` | `/api/chat` | Stream a reply (SSE: `token` / `done` / `error`). |
| `GET` | `/api/conversations` | List saved conversations. |
| `GET` | `/api/conversations/{id}` | Get a conversation's messages. |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation. |

---

## License

Released under the MIT License.
