# Smart OPD Queue Predictor

Full-stack hackathon starter for approximate OPD waiting-time prediction and live queue updates.

## Project architecture

```text
smart-opd-queue-predictor/
|-- src/
|   |-- App.jsx              React patient, reception, doctor and analytics views
|   |-- api.js               Fetch client for FastAPI routes
|   |-- main.jsx             React entry point
|   |-- styles.css            Product visual system
|   `-- responsive.css       Responsive dashboard styles
|-- backend/
|   |-- main.py              FastAPI routes and queue orchestration
|   |-- database.py          SQLAlchemy engine and sessions
|   |-- models.py            Database tables and relationships
|   |-- schemas.py           Request validation models
|   |-- ml_model.py          Scikit-learn regression predictor
|   |-- requirements.txt     Python dependencies
|   `-- .env.example         Runtime configuration template
|-- index.html
|-- package.json
`-- vite.config.js
```

The React app continues to provide a localStorage-backed demo. The FastAPI service is the production-shaped integration boundary and defaults to SQLite; set `DATABASE_URL` to a PostgreSQL connection string for deployment.

## Database schema

- `doctors`: provider, department, availability, and average consultation duration.
- `patients`: patient demographics and assigned doctor.
- `tokens`: token number, queue position, status, and consultation timestamps.
- `appointments`: scheduled patient/doctor appointments.
- `queue_history`: append-only queue events for audit and analytics.

Relationships: `Doctor 1:N Patient`, `Patient 1:N Token`, and `Token 1:N QueueHistory`.

## ML prediction engine

`backend/ml_model.py` trains a deterministic `sklearn.linear_model.LinearRegression` model from synthetic historical queue examples. Features are:

1. Patients ahead
2. Average consultation time
3. Doctor availability (`1.0` available, `1.25` unavailable)
4. Queue movement multiplier

The output is rounded to an approximate number of minutes with a minimum of four minutes. This is demo data and is explicitly **not medically validated**. A production system should train and monitor the model with de-identified hospital history, evaluate error bounds, and avoid using it for urgent clinical decisions.

## API endpoints

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/patient/register` | Register a patient and assign the next token |
| `GET` | `/queue/status` | Return active queue and current consulting token |
| `GET` | `/waiting-time/{token}` | Return position and estimated wait for a token |
| `POST` | `/doctor/start` | Start a consultation |
| `POST` | `/doctor/end` | Complete a consultation and advance the queue |
| `POST` | `/reception/doctor` | Add a doctor/provider |
| `GET` | `/analytics` | Return daily operational metrics |
| `POST` | `/api/predict` | Run the regression prediction directly |
| `POST` | `/api/transcribe` | Transcribe audio with Whisper when configured |
| `POST` | `/api/prediction-explanation` | Generate a GPT explanation or local fallback |
| `GET` | `/api/health` | Check service and integration status |

## Local deployment

### Frontend

```powershell
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --port 8000
```

Backend docs: `http://localhost:8000/docs`

### Optional integrations

Set `OPENAI_API_KEY` in `backend/.env` to enable Whisper. Set `USE_LLM=true` to enable GPT explanations. For PostgreSQL, replace `DATABASE_URL` with a SQLAlchemy PostgreSQL URL and install a matching driver such as `psycopg[binary]`.

## Production checklist

- Add authentication and role-based permissions for reception and doctors.
- Add WebSocket or Server-Sent Events for push queue updates.
- Add migrations with Alembic instead of `create_all`.
- Add SMS/WhatsApp provider adapters with consent and delivery logs.
- Add QR token generation and hospital/department tenancy.
- Replace synthetic training data with evaluated, de-identified historical data.
- Add automated tests, rate limiting, structured logging, secrets management, and HTTPS.
