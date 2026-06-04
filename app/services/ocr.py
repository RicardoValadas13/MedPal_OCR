import base64
import json

from ..config import get_settings
from ..models import PrescriptionResponse

_SYSTEM = (
    "You are a medical prescription OCR engine. You receive a photo or scan of a "
    "prescription and extract its contents into structured JSON. The prescription "
    "may list medications, physiotherapy/exercise instructions, or both. Read the "
    "image carefully, including handwriting, and never invent items that are not "
    "present. If a field is not visible or not applicable, set it to null."
)

# The output schema is described to the model in plain language so it returns a
# json_object we can validate with Pydantic. The `description` field is the key
# output: it is fed to the MedPal GIF Generation API as its `action` prompt, so it
# must be a vivid, self-contained visual instruction that an image generator can
# depict — not a terse label.
_INSTRUCTIONS = (
    "Return a JSON object with this exact shape:\n"
    "{\n"
    '  "prescription_type": "medication" | "physiotherapy" | "mixed",\n'
    '  "language": "<ISO code, e.g. \\"pt\\", \\"en\\">",\n'
    '  "patient": { "name": string|null, "age": integer|null } | null,\n'
    '  "prescriber": { "name": string|null } | null,\n'
    '  "date": "<YYYY-MM-DD or null>",\n'
    '  "items": [\n'
    "    {\n"
    '      "type": "medication" | "physiotherapy",\n'
    '      "name": "<drug name with strength, or exercise name>",\n'
    '      "description": "<vivid 1-2 sentence visual instruction in English, see rules>",\n'
    '      "dosage": "<amount per single intake, e.g. \\"1 comprimido\\", \\"500 mg\\">|null",\n'
    '      "duration_days": integer|null,\n'
    '      "schedule": <FixedSchedule or IntervalSchedule, see rules> | null,\n'
    '      "sets": integer|null,\n'
    '      "reps": integer|null\n'
    "    }\n"
    "  ],\n"
    '  "warnings": ["<anything illegible or uncertain>"]\n'
    "}\n\n"
    "Rules:\n\n"
    "## description\n"
    "Every item MUST have a `description`: sent directly to an image/animation "
    "generator, so make it vivid and self-contained (1-2 sentences, English). "
    "Describe WHO does WHAT with WHICH object/body part with enough visual context "
    "for an illustrator to draw it without seeing the prescription. "
    "Do NOT include dosages, numbers, brand names, or schedule details. "
    "Examples: \"A person holds a glass of water in one hand and a single pill in the "
    "other, then places the pill in their mouth and swallows it.\"; \"A person slowly "
    "raises one arm overhead to stretch the shoulder, keeping the back straight.\"\n\n"
    "## dosage\n"
    "Amount taken per single intake ONLY — e.g. \"1 comprimido\", \"500 mg\", "
    "\"2 pulverizações em cada narina\". Never include frequency or timing.\n\n"
    "## duration_days\n"
    "Convert the treatment duration to an integer number of days: "
    "\"5 dias\" → 5, \"1 semana\" → 7, \"2 semanas\" → 14, \"1 mês\" → 30, "
    "\"3 meses\" → 90. Set to null if no duration is stated.\n\n"
    "## schedule\n"
    "Choose ONE of two shapes based on how the prescription expresses the frequency:\n\n"
    "**IntervalSchedule** — use when the prescription says 'every N hours' "
    "(\"de 8 em 8 horas\", \"de 12 em 12 horas\", \"every 6 hours\", etc.):\n"
    "{\n"
    '  "type": "interval",\n'
    '  "interval_hours": <integer, e.g. 8>,\n'
    '  "first_dose": "<HH:MM of the first dose, default \\"08:00\\" if not stated>",\n'
    '  "days": ["Mon"|"Tue"|"Wed"|"Thu"|"Fri"|"Sat"|"Sun", ...],\n'
    '  "take_with_food": true|false\n'
    "}\n\n"
    "**FixedSchedule** — use for everything else (\"twice daily\", \"morning and night\", "
    "\"3x/day\", \"once daily\", explicit times, etc.):\n"
    "{\n"
    '  "type": "fixed",\n'
    '  "times": ["HH:MM", ...],\n'
    '  "days": ["Mon"|"Tue"|"Wed"|"Thu"|"Fri"|"Sat"|"Sun", ...],\n'
    '  "take_with_food": true|false\n'
    "}\n\n"
    "Time inference for FixedSchedule:\n"
    "  \"once daily\" / \"morning\" → [\"08:00\"]\n"
    "  \"twice daily\" / \"morning and night\" → [\"08:00\", \"20:00\"]\n"
    "  \"3x/day\" → [\"08:00\", \"14:00\", \"20:00\"]\n"
    "  \"4x/day\" → [\"08:00\", \"12:00\", \"16:00\", \"20:00\"]\n"
    "  \"at night\" / \"ao deitar\" → [\"22:00\"]\n"
    "  Use exact times if written on the prescription.\n\n"
    "Days inference (both schedule types):\n"
    "  No day restriction / \"daily\" → all seven days.\n"
    "  \"weekdays\" → [\"Mon\",\"Tue\",\"Wed\",\"Thu\",\"Fri\"].\n"
    "  Only restrict when the prescription explicitly says so.\n\n"
    "take_with_food: true if the prescription says \"with food\", \"after meals\", "
    "\"após as refeições\", \"com alimentos\", or any equivalent; false otherwise.\n\n"
    "## physiotherapy items\n"
    "Use `sets`/`reps`; set all medication fields (dosage, duration_days, schedule) to null.\n\n"
    "## general\n"
    "- `prescription_type` is \"mixed\" only if there are both medication and physiotherapy items.\n"
    "- Add a short note to `warnings` for anything you could not read confidently.\n"
    "- Output ONLY the JSON object, no prose."
)


def extract_prescription(client, image_bytes: bytes, mime_type: str) -> PrescriptionResponse:
    """Send the image to the vision model and parse the result into our schema."""
    settings = get_settings()
    b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:{mime_type};base64,{b64}"

    resp = client.chat.completions.create(
        model=settings.ocr_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _INSTRUCTIONS},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(resp.choices[0].message.content)
    return PrescriptionResponse.model_validate(data)
