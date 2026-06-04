# MedPal Prescription OCR

A FastAPI microservice for **MedPal**. It takes a photo or scan of a medical
prescription (medications, physiotherapy, or both) and returns structured JSON
using an OpenAI vision model.

Each extracted item carries a `description` — a short imperative action phrased
exactly the way the [MedPal GIF Generation API](../MedPal_GIFGeneration) expects
its `action` field — so the backend can feed prescription items straight into GIF
generation.

## Run locally

```bash
cd MedPal_PrescriptionOCR
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
uvicorn app.main:app --reload
```

Then:

```bash
curl -s -X POST http://localhost:8000/v1/prescriptions \
  -F "file=@prescription.jpg" | python -m json.tool
```

## Endpoints

- `POST /v1/prescriptions` — multipart image upload (`file`).
- `POST /v1/prescriptions:base64` — JSON body `{ "image_base64": "...", "mime_type": "image/jpeg" }`.
- `GET /health` — readiness check.

See [INTEGRATION.md](INTEGRATION.md) for the full contract.

## Notes

- **Synchronous:** one vision call (~2–10s), returned in a single HTTP response.
  If accuracy/latency on real images proves poor, the next step is to switch to a
  job+poll pattern like the GIF service.
- **Model:** `gpt-4o` by default (`OCR_MODEL` env var to override, e.g.
  `gpt-4o-mini` for lower cost).
- **Mockup:** no auth and no compliance handling; do not send real patient data.
