# MedPal Prescription OCR API — Integration Guide

> Audience: an AI coding assistant (or developer) integrating this service into
> another project. This document is self-contained and describes the exact
> contract. Follow it literally.

## What this service does

Given an image of a medical prescription, it returns structured JSON describing
the prescribed medications and/or physiotherapy exercises. Each item includes a
`description` field that is a short imperative action ready to be passed as the
`action` field to the MedPal GIF Generation API.

Processing is **synchronous**: one HTTP request in, the JSON out (~2–10s). There
is no job/polling step.

```
POST /v1/prescriptions          (multipart image)  -> 200 { prescription_type, items, ... }
POST /v1/prescriptions:base64   (base64 JSON)       -> 200 { prescription_type, items, ... }
GET  /health                                        -> 200 { "status": "ok" }
```

## Base URL & auth

- **Base URL:** set per environment, e.g. `https://medpal-prescription-ocr.onrender.com`.
- **Auth:** none (mockup). The OpenAI key is configured server-side and is never
  sent by the client. Add auth in front if you deploy publicly.

## Endpoints

### 1. Read prescription (multipart) — `POST /v1/prescriptions`

- Content type: `multipart/form-data`.
- Field: `file` — the image. Allowed types: `image/jpeg`, `image/png`,
  `image/webp`, `image/gif`. Max size: 15 MB.

### 2. Read prescription (base64) — `POST /v1/prescriptions:base64`

- Content type: `application/json`.

```json
{ "image_base64": "<base64 bytes, no data URI prefix>", "mime_type": "image/jpeg" }
```

### Success response — HTTP 200 (both endpoints)

```json
{
  "prescription_type": "mixed",
  "language": "pt",
  "patient": { "name": "Maria Silva", "age": null },
  "prescriber": { "name": "Dr. João Costa" },
  "date": "2026-06-01",
  "items": [
    {
      "type": "medication",
      "name": "Ibuprofeno 400mg",
      "description": "take this pill",
      "dosage": "400 mg",
      "frequency": "2x per day",
      "duration": "5 days",
      "quantity": "1 box",
      "instructions": "after meals",
      "sets": null,
      "reps": null
    },
    {
      "type": "physiotherapy",
      "name": "Shoulder stretch",
      "description": "raise your arm for a shoulder stretch",
      "dosage": null,
      "frequency": "daily",
      "duration": null,
      "quantity": null,
      "instructions": null,
      "sets": 3,
      "reps": 10
    }
  ],
  "warnings": []
}
```

Field reference:

| Field                | Type     | Notes |
|----------------------|----------|-------|
| `prescription_type`  | string   | `medication` \| `physiotherapy` \| `mixed`. |
| `language`           | string   | ISO code of the detected document language. |
| `patient`            | object   | `{ name, age }`; either may be null; object may be null. |
| `prescriber`         | object   | `{ name }`; may be null. |
| `date`               | string   | `YYYY-MM-DD` or null. |
| `items[].type`       | string   | `medication` \| `physiotherapy`. |
| `items[].name`       | string   | Drug name (with strength) or exercise name. |
| `items[].description`| string   | **Short imperative action — pass as `action` to the GIF API.** Always present. |
| `items[].dosage/frequency/duration/quantity/instructions` | string\|null | Medication fields. |
| `items[].sets/reps`  | int\|null | Physiotherapy fields. |
| `warnings`           | string[] | Anything illegible or uncertain. |

### Error responses

- `400` — empty image / invalid base64.
- `413` — image too large.
- `415` — unsupported image type.
- `502` — the vision model call or JSON parse failed.

## End-to-end pattern: OCR → GIF

```python
import requests

OCR_URL = "https://medpal-prescription-ocr.onrender.com"
GIF_URL = "https://medpal-gifgen.onrender.com"

# 1. OCR the prescription image.
with open("prescription.jpg", "rb") as f:
    rx = requests.post(f"{OCR_URL}/v1/prescriptions", files={"file": f}).json()

# 2. For each item, generate an instructional GIF from its `description`.
for item in rx["items"]:
    job = requests.post(
        f"{GIF_URL}/v1/gifs",
        json={"action": item["description"], "language": rx["language"]},
    ).json()
    # ...then poll GET /v1/gifs/{job_id} until status == "done" (see GIF API guide).
    print(item["name"], "->", job["job_id"])
```

## Operational notes

- **Latency:** ~2–10s per image; integrate as a normal synchronous request.
  Allow a generous client timeout (e.g. 60s) for cold starts on a free host.
- **Accuracy:** quality depends on the photo. Handwriting and poor lighting may
  populate `warnings`. If results are unreliable, switch the server to a job+poll
  pipeline and/or a higher-fidelity model.
- **No idempotency:** each call re-runs the model. Cache on the caller side if
  needed.
- **No client API key:** never send OpenAI keys to this service; it holds its own.
