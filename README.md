# Professional Relations Platform — Version 1

A private Streamlit application for territory planning, visit execution, relationship memory, referral analysis, leadership publication, and reporting.

## Current build status

The **Foundation module** is implemented:

- Shared database connection layer
- PostgreSQL support for free hosted storage
- Local SQLite development fallback
- Transaction helper
- Migration runner and migration tracking
- Consultant and Leadership authentication shell
- Streamlit configuration and secrets template
- Existing Territory Route Planner functionality preserved during modular migration

The frozen engineering specification remains the implementation source of truth.

## Project structure

```text
app.py
config.py
database/
  connection.py
  migrations.py
  schema.py
services/
  auth_service.py
.streamlit/
  config.toml
  secrets.toml.example
```

## Local setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

When no users are configured, local development opens as the Consultant role. This fallback is disabled when `[auth]` users are configured in Streamlit secrets.

## Hosted database

Version 1 expects a PostgreSQL-compatible hosted relational database. Put the SQLAlchemy connection URL in Streamlit secrets:

```toml
DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
```

The app applies foundation migrations at startup. The local Streamlit filesystem is not treated as authoritative production storage.

## Authentication configuration

Use `.streamlit/secrets.toml.example` as the template. Add one or more users with the exact role `Consultant` or `Leadership`. Do not commit real passwords or database credentials.

## Streamlit Community Cloud

1. Upload the project files to GitHub.
2. Create or open the app in Streamlit Community Cloud.
3. Set the main file path to `app.py`.
4. Add the database and authentication values under **App settings → Secrets**.
5. Deploy or reboot the app.
