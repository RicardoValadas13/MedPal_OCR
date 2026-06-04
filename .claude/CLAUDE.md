# MedPal Prescription OCR — Claude Context

## What this service does

FastAPI microservice that receives a prescription image and returns structured JSON
using an OpenAI vision model (`gpt-4o` by default). Part of the MedPal ecosystem.

## Architecture

```
app/
  main.py          — FastAPI routes + validation (400/413/415/502 error handling)
  models.py        — Pydantic models: PrescriptionResponse, PrescriptionItem,
                     FixedSchedule, IntervalSchedule, Patient, Prescriber
  config.py        — Settings via pydantic-settings (OPENAI_API_KEY, OCR_MODEL,
                     MAX_IMAGE_BYTES)
  services/
    ocr.py         — OpenAI vision call + prompt (_SYSTEM, _INSTRUCTIONS)
```

## Key design decisions

- **Synchronous:** one vision call per request, response returned immediately.
  No job/poll pattern.
- **Structured schedule output:** every medication item includes a `schedule`
  object that maps directly to the medication form — no extra parsing needed.
- **Two schedule types** (discriminated union on `type`):
  - `FixedSchedule` — explicit times, e.g. `["08:00", "20:00"]`
  - `IntervalSchedule` — repeating interval, e.g. every 8 hours from 08:00
- **`description` field** is reserved for the MedPal GIF Generation API — must
  be a vivid visual instruction in English, no numbers or dosages.
- The prompt lives entirely in `ocr.py` (`_SYSTEM` + `_INSTRUCTIONS`). Change
  OCR behaviour by editing those strings, not the models.

## PrescriptionItem fields (medications)

| Field          | Description                                                              |
|----------------|--------------------------------------------------------------------------|
| `name`         | Drug name with strength, e.g. "Ben-u-ron 1000mg"                        |
| `description`  | Vivid visual instruction → passed as `action` to the GIF API            |
| `dosage`       | Amount per single intake, e.g. "1 comprimido", "500 mg"                 |
| `duration_days`| Treatment duration as integer days (7 = 1 week, 30 = 1 month); null if ongoing |
| `schedule`     | FixedSchedule or IntervalSchedule (see below)                            |

## Schedule → form field mapping

### FixedSchedule
```json
{
  "type": "fixed",
  "times": ["08:00", "20:00"],
  "days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
  "take_with_food": false
}
```
| Field           | Form element              |
|-----------------|---------------------------|
| `times`         | HH:MM time buttons        |
| `days`          | Mon–Sun day toggles       |
| `take_with_food`| "Take with food" toggle   |

### IntervalSchedule
```json
{
  "type": "interval",
  "interval_hours": 8,
  "first_dose": "08:00",
  "days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
  "take_with_food": false
}
```
| Field           | Form element                        |
|-----------------|-------------------------------------|
| `interval_hours`| "A cada X horas" selector           |
| `first_dose`    | "Primeira dose" time picker         |
| `days`          | Mon–Sun day toggles                 |
| `take_with_food`| "Take with food" toggle             |

Use `IntervalSchedule` when the prescription says "de 8 em 8 horas", "every 6 hours", etc.
Use `FixedSchedule` for everything else ("twice daily", "morning and night", "3x/day").

## Sibling services

- **MedPal GIF Generation API** — receives `item.description` as its `action`
  field and returns an instructional GIF. Documented at `../MedPal_GIFGeneration`.

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY
uvicorn app.main:app --reload
```

Test with:
```bash
curl -s -X POST http://localhost:8000/v1/prescriptions \
  -F "file=@prescription.jpg" | python -m json.tool
```

## Env vars

| Variable          | Default   | Notes                                    |
|-------------------|-----------|------------------------------------------|
| `OPENAI_API_KEY`  | required  |                                          |
| `OCR_MODEL`       | `gpt-4o`  | Use `gpt-4o-mini` for lower cost/latency |
| `MAX_IMAGE_BYTES` | 15728640  | 15 MB                                    |

## Deployment

Configured for Render (`render.yaml`). Deployed at
`https://medpal-prescription-ocr.onrender.com`. No auth — add a proxy layer
before exposing publicly. Never send real patient data (mockup only).
