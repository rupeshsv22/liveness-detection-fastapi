# Face Liveness Detection API

eKYC face liveness detection over WebSocket. Built with FastAPI, MediaPipe, and OpenCV.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker build -t face-liveness .
docker run -p 8000:8000 face-liveness
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/liveness/start` | Create a session, get challenge list |
| WS | `/api/liveness/stream/{session_id}` | Stream frames, receive real-time feedback |
| GET | `/api/liveness/result/{session_id}` | Fetch final result |
| GET | `/health` | Health check |

Interactive docs: `http://localhost:8000/docs`

## WebSocket Frame Format

**Client → Server:**
```json
{ "frame": "<base64 JPEG>", "timestamp": 1234567890 }
```

**Server → Client (per frame):**
```json
{
  "face_detected": true,
  "face_count": 1,
  "current_challenge": { "type": "BLINK", "instruction": "Blink your eyes once", "order": 1 },
  "challenge_completed": false,
  "spoof_score": 0.08,
  "spoof_detected": false,
  "message": "Blink your eyes once",
  "error": null
}
```

**Server → Client (on completion):**
```json
{ "session_complete": true, "liveness_score": 87.5, "passed": true }
```

## Challenges

| Type | Trigger Condition |
|------|------------------|
| `BLINK` | EAR < 0.21 for ≥2 frames then rises |
| `BLINK_TWICE` | Two blinks within 5 seconds |
| `TURN_LEFT` | Head yaw < −25° |
| `TURN_RIGHT` | Head yaw > 25° |
| `NOD` | Pitch change > 15° down then back up within 2 s |

## Scoring

```
score = challenges_ratio × 60 + (1 − avg_spoof) × 30 + speed_bonus × 10
```

Pass threshold: **70.0**. Any spoof detection → auto-fail.

## Configuration

All thresholds live in `app/config.py`. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `EAR_THRESHOLD` | 0.21 | Eye aspect ratio blink threshold |
| `HEAD_YAW_THRESHOLD` | 25.0° | Head turn angle |
| `SPOOF_THRESHOLD` | 0.6 | LBP spoof score cutoff |
| `SESSION_TIMEOUT` | 60 s | Inactivity expiry |
| `LIVENESS_PASS_THRESHOLD` | 70.0 | Minimum passing score |

Set `ALLOWED_ORIGINS` env var for CORS (comma-separated, default `*`).
