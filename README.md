# PolicyPulse

Regulatory intelligence monitor for USCIS policy content.

## Setup

1. Clone the repository.
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your values.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (Supabase) |
| `BRIGHT_DATA_API_KEY` | Bright Data API key |
| `BRIGHT_DATA_SERP_ZONE` | Bright Data SERP zone name |
| `BRIGHT_DATA_UNLOCKER_ZONE` | Bright Data Web Unlocker zone name |
| `ENVIRONMENT` | Runtime environment (`development`, `production`, etc.) |

## Running locally

```bash
uvicorn main:app --reload
```

The health check is available at `http://127.0.0.1:8000/`.

## Deployment

PolicyPulse is configured for [Railway](https://railway.app) via `railway.toml`. Set the environment variables in your Railway project dashboard, then deploy. The service starts with:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```
