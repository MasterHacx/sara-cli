# SARA v1.0 — Secure Autonomous Response Agent

> An AI-powered autonomous CLI agent that can execute tasks, generate code, and learn new skills on the fly.

## Features

- **Dual AI Backend** — Gemini (primary) + Groq Kimi K2 (fallback) with automatic failover
- **Smart Intent Detection** — LLM-powered classification distinguishes tasks from chat
- **ReAct Task Engine** — Think → Act → Observe loop for complex multi-step tasks
- **Auto-Grounding** — Automatically searches the web for factual/current queries
- **Skill System** — SARA can write, register, and reuse Python skills permanently
- **Long-Term Memory** — Auto-extracts facts from conversations into persistent memory
- **Background Mode** — Heartbeat mode monitors system health and processes `todo.txt`
- **Dual Personality** — Angel mode (professional) and Evil mode (unrestricted)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys in config.json
#    - api_key: Your Google Gemini API key
#    - groq_api_key: Your Groq API key

# 3. Run SARA
python main.py

# Or on Windows:
run.bat
```

## Project Structure

```
sara_cli/
├── core/
│   ├── sara.py          # Main agent (SkillManager, SaraAgent, ReAct loop)
│   └── llm_client.py    # Multi-provider LLM manager (Gemini + Groq)
├── database/            # User contacts for messaging skills
├── docs/                # User guide and documentation
├── skills/              # Auto-populated skill scripts
├── config.json          # API keys, models, and agent settings
├── main.py              # Entry point
├── skills.json          # Skill registry (auto-managed)
├── soul.md              # Agent's mission manifest
└── todo.txt             # Background mode task queue
```

## Key Commands

| Command                    | Description                   |
| -------------------------- | ----------------------------- |
| `help`                     | Show all commands             |
| `skills`                   | List registered skills        |
| `setup`                    | Install optional dependencies |
| `mode angel` / `mode evil` | Switch personality            |
| `heartbeat`                | Start background monitoring   |
| `remember <key> = <value>` | Save to memory                |
| `recall <keyword>`         | Search memory                 |
| `history`                  | Show chat history             |
| `clear`                    | Clear chat history            |
| `exit`                     | Exit SARA                     |

## Configuration

Edit `config.json` to customize:

- **API Keys** — `api_key` (Gemini), `groq_api_key` (Groq)
- **Models** — `text_models` list, `groq_model`
- **Provider** — `primary_provider` (`gemini` or `groq`)
- **Behavior** — `execution_mode` (`admin` = confirm before run, `auto` = run immediately)
- **Limits** — `max_task_steps`, `script_timeout`, `max_output_tokens`

## Created by MasterHacx
