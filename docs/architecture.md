# crawllmer Architecture

The system follows a hexagonal architecture: domain and application core are isolated
from web, storage, and crawl strategy adapters.

```mermaid
flowchart LR
    UI[Streamlit UI\nInterface Layer] --> APP[Application Orchestrator]
    API[FastAPI API\nInterface Layer] --> APP

    APP --> DOMAIN[Domain Models\nPydantic]
    APP --> PORTS[Ports\nStrategy + Repository]

    PORTS --> STRATS[Strategies Adapter\nDirect, Robots, Metadata, Browser, Archive]
    PORTS --> REPO[SQLite Repository\nSQLModel]

    STRATS --> WEB[(Target Website)]
    REPO --> DB[(SQLite)]

    APP --> OBS[Logging / OTEL-ready diagnostics]
```

## Runtime topology

- **API process**: Uvicorn serving FastAPI (`/health`, `/api/v1/*`).
- **UI process**: Streamlit app for operators and users.
- **Shared core**: Both UI and API invoke the same orchestrator/runtime module.
- **Persistence**: SQLite file stores crawl history and strategy outcomes.
