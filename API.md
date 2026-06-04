# MedPal Prescription OCR — How the API Works

A FastAPI service that turns a photo/scan of a medical prescription into
structured JSON, using an OpenAI vision model. Part of the **MedPal** ecosystem:
each extracted item includes a `description` action string designed to be passed
straight into the [MedPal GIF Generation API](../MedPal_GIFGeneration).

**Live base URL:** `https://medpal-prescription-ocr.onrender.com`

---

## 1. What happens on a request (the flow)

```
client ──image──▶ FastAPI endpoint
                     │  1. validate (type / size / non-empty)
                     │  2. base64-encode → data URI
                     ▼
                  OpenAI vision model (gpt-4o)
                     │  reads the image, follows a strict prompt,
                     │  returns a JSON object (response_format=json_object)
                     ▼
                  Pydantic validates the JSON → PrescriptionResponse
                     ▼
client ◀── 200 JSON ─┘
```

- **Synchronous:** one HTTP request in, the JSON out (~2–10s). No jobs, no polling.
- **Stateless:** nothing is stored; each call re-runs the model.
- The model is instructed to **never invent** items and to set unknown fields to
  `null`, adding a note to `warnings` for anything illegible.

Source map:
- `app/main.py` — endpoints, validation, error handling.
- `app/services/ocr.py` — the prompt and the OpenAI call.
- `app/models.py` — the response schema.
- `app/config.py` — settings (`OPENAI_API_KEY`, `OCR_MODEL`, max image size).

---

## 2. Endpoints

| Method & path                   | Body                                              | Returns |
|---------------------------------|---------------------------------------------------|---------|
| `GET  /health`                  | —                                                 | `{"status":"ok"}` |
| `POST /v1/prescriptions`        | `multipart/form-data`, field `file` = image       | `PrescriptionResponse` |
| `POST /v1/prescriptions:base64` | JSON `{ "image_base64": "...", "mime_type": "..." }` | `PrescriptionResponse` |

- **Allowed image types:** `image/jpeg`, `image/png`, `image/webp`, `image/gif`.
- **Max size:** 15 MB.
- **Auth:** none (mockup). The OpenAI key lives server-side; never send it.
- Interactive docs are available at `/docs` (Swagger UI).

Use `multipart` for normal uploads; use `:base64` for backend-to-backend calls
where the image is already in memory as a base64 string.

---

## 3. The response schema

```jsonc
{
  "prescription_type": "medication" | "physiotherapy" | "mixed",
  "language": "pt",                       // ISO code of the detected language
  "patient":    { "name": "string|null", "age": "int|null" } | null,
  "prescriber": { "name": "string|null" } | null,
  "date": "YYYY-MM-DD | null",
  "items": [
    {
      "type": "medication" | "physiotherapy",
      "name": "string",                   // drug (with strength) or exercise name
      "description": "string",            // SHORT IMPERATIVE ACTION — feeds GIF API
      // medication fields (null for physiotherapy):
      "dosage": "string|null",
      "frequency": "string|null",
      "duration": "string|null",
      "quantity": "string|null",
      "instructions": "string|null",
      // physiotherapy fields (null for medication):
      "sets": "int|null",
      "reps": "int|null"
    }
  ],
  "warnings": ["anything illegible or uncertain"]
}
```

**The important field is `items[].description`.** It is always present and is a
concise, English, imperative action (e.g. `"take this pill"`,
`"use the oxygen concentrator"`) — exactly the shape the GIF Generation API
expects as its `action`.

---

## 4. Examples

### Multipart upload

```bash
curl -s -X POST https://medpal-prescription-ocr.onrender.com/v1/prescriptions \
  -F "file=@prescription.png" | python3 -m json.tool
```

### Base64 (JSON)

```bash
# build payload then POST
B64=$(base64 -i prescription.png)
printf '{"image_base64":"%s","mime_type":"image/png"}' "$B64" > payload.json
curl -s -X POST https://medpal-prescription-ocr.onrender.com/v1/prescriptions:base64 \
  -H "Content-Type: application/json" --data @payload.json | python3 -m json.tool
```

### Sample response

```json
{
  "prescription_type": "physiotherapy",
  "language": "pt",
  "patient": { "name": "FERNANDO MANUEL DURÃO DE ORNELAS REZENDE", "age": null },
  "prescriber": { "name": "PEDRO DAMIÃO" },
  "date": "2021-11-16",
  "items": [
    {
      "type": "physiotherapy",
      "name": "Oxigenoterapia, Concentrador de Oxigénio",
      "description": "use the oxygen concentrator",
      "dosage": null, "frequency": null, "duration": null,
      "quantity": null, "instructions": "Fluxo: 2 L/min Horas / Dia: 15",
      "sets": null, "reps": null
    }
  ],
  "warnings": []
}
```

> Note: responses are UTF-8. If you see `ÃO` in a terminal, that's just
> ASCII-escaped output (e.g. `python -m json.tool`); the decoded value is `Ã`.

---

## 5. Errors

| Status | Meaning |
|--------|---------|
| `400`  | Empty image or invalid base64. |
| `413`  | Image larger than the configured limit (15 MB). |
| `415`  | Unsupported image MIME type. |
| `422`  | Request body failed validation (e.g. missing `image_base64`). |
| `500`  | `OPENAI_API_KEY` not configured on the server. |
| `502`  | The vision model call or JSON parsing failed (detail includes the cause). |

---

## 6. Chaining into the GIF API

The reason `description` exists: loop over the items and generate an
instructional GIF for each.

```python
import requests

OCR_URL = "https://medpal-prescription-ocr.onrender.com"
GIF_URL = "https://medpal-gifgen.onrender.com"

with open("prescription.png", "rb") as f:
    rx = requests.post(f"{OCR_URL}/v1/prescriptions", files={"file": f}).json()

for item in rx["items"]:
    job = requests.post(
        f"{GIF_URL}/v1/gifs",
        json={"action": item["description"], "language": rx["language"]},
    ).json()
    # then poll GET /v1/gifs/{job_id} until status == "done"
    print(item["name"], "->", job["job_id"])
```

---

## 7. Configuration (env vars)

| Var               | Default   | Purpose |
|-------------------|-----------|---------|
| `OPENAI_API_KEY`  | —         | **Required.** Server-side OpenAI key. |
| `OCR_MODEL`       | `gpt-4o`  | Vision model. `gpt-4o-mini` is cheaper/less accurate. |
| `MAX_IMAGE_BYTES` | `15728640`| Upload size limit in bytes. |

---

## 8. Notes & limits

- **Mockup:** no auth, no compliance handling — do not send real patient data.
- **Cold starts:** on Render's free plan the service sleeps when idle; the first
  request can take ~30–60s while it wakes (a router 404 with header
  `x-render-routing: no-server` means it isn't up yet — just retry).
- **Accuracy** depends on image quality; handwriting/poor lighting may populate
  `warnings`. If results are unreliable, switch to a job+poll pipeline and/or a
  higher-fidelity model.
- **No idempotency:** each call re-runs the model; cache on the caller side if needed.
