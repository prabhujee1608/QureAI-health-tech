# QureAI API

FastAPI service for the React prototype.

## Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --port 8000
```

The API is mock-safe by default:

- `GET /api/health` checks service status.
- `POST /api/predict` calculates a simulated wait estimate.
- `POST /api/transcribe` uses the Whisper API when `OPENAI_API_KEY` is set.
- `POST /api/prediction-explanation` uses GPT when `USE_LLM=true`; otherwise it returns a local explanation.

These are prototype estimates and are not medically validated.
