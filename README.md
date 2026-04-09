This project is a local-first desktop assistant agent designed to explore advanced agent system design.

Instead of focusing on UI or chatbot interaction, this system emphasizes:
- tool-based reasoning and execution
- task routing and planning
- persistent memory
- event-driven architecture
- safe action handling with approval gates
- traceable and debuggable agent workflows

The goal is to better understand how modern AI agents operate beyond simple chat interfaces.

## Features

- 🧠 Routing system (chat / tool / planning)
- 📋 Task planning for multi-step requests
- 🔧 Tool calling with structured schemas
- 💾 Persistent memory (facts & history)
- ⚡ Event-driven inputs (user + system)
- 🔐 Approval gate for sensitive actions
- 📊 Trace logging for debugging agent decisions

## Architecture
```
desktop-assistant-agent/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── executor.py
│   ├── logger.py
│   ├── memory.py
│   ├── router.py
│   └── schemas.py
│   └── tools/
│       ├── __init__.py
│       ├── registry.py
│       └── system_tools.py
├── data/
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

## Example Use Cases

- Open applications
- Create notes
- Store and recall user preferences
- Break down complex tasks into steps

## Tech Stack

- Python
- OpenAI Responses API
- Pydantic
- Local JSON storage

## Roadmap

- [ ] Add file system tools
- [ ] Add browser / web search tool
- [ ] Add event bus (window, clipboard)
- [ ] Add multi-agent / delegation