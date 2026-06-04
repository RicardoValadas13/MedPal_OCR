# MedPal Prescription OCR — Claude Context

## What this service does

FastAPI microservice that receives a prescription image and returns structured JSON
using an OpenAI vision model (`gpt-4o` by default). Part of the MedPal ecosystem.

## Architecture

```
app/
  main.py          — FastAPI routes + validation (400/413/415/502 error handling)
  models.py        — Pydantic models: PrescriptionResponse, PrescriptionItem,
                     MedicationSchedule, Patient, Prescriber
  config.py        — Settings via pydantic-settings (OPENAI_API_KEY, OCR_MODEL,
                     MAX_IMAGE_BYTES)
  services/
    ocr.py         — OpenAI vision call + prompt (_SYSTEM, _INSTRUCTIONS)
```

## Key design decisions

- **Synchronous:** one vision call per request, response returned immediately.
  No job/poll pattern.
- **Structured schedule output:** every medication item includes a `schedule`
  object (`times`, `days`, `take_with_food`) derived from the free-text fields,
  so callers can populate a medication-schedule form directly without extra parsing.
- **`description` field** is reserved for the MedPal GIF Generation API — it must
  be a vivid visual instruction in English, no numbers or dosages.
- The prompt lives entirely in `ocr.py` (`_SYSTEM` + `_INSTRUCTIONS`). Change
  OCR behaviour by editing those strings, not the models.

## Field separation rules (medication items)

| Field         | What it captures                                                                 |
|---------------|----------------------------------------------------------------------------------|
| `dosage`      | Amount per single intake — e.g. "1 comprimido", "500 mg"                        |
| `frequency`   | How often — e.g. "3 vezes por dia", "de 8 em 8 horas"                          |
| `duration`    | Treatment period as written — e.g. "5 dias", "1 semana"                         |
| `duration_days` | Duration converted to integer days (7 → "1 semana", 30 → "1 mês")            |
| `quantity`    | Total units dispensed — e.g. "30 comprimidos", "1 embalagem". Calculated from dosage × frequency × duration if not explicit. |
| `instructions`| Other notes — e.g. "após as refeições", "ao deitar"                            |

## MedicationSchedule → form field mapping

| `schedule` field   | Form element                         |
|--------------------|--------------------------------------|
| `times`            | `["08:00", "20:00"]` time buttons    |
| `days`             | `["Mon"…"Sun"]` day toggle buttons   |
| `take_with_food`   | "Take with food" boolean toggle      |

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
