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
    '  "language": "<ISO code of the document language, e.g. \\"pt\\", \\"en\\">",\n'
    '  "patient": { "name": string|null, "age": integer|null } | null,\n'
    '  "prescriber": { "name": string|null } | null,\n'
    '  "date": "<YYYY-MM-DD or null>",\n'
    '  "items": [\n'
    "    {\n"
    '      "type": "medication" | "physiotherapy",\n'
    '      "name": "<drug name with strength, or exercise name>",\n'
    '      "description": "<a vivid 1-2 sentence visual instruction in English, see rules>",\n'
    '      "dosage": string|null, "frequency": string|null, "duration": string|null,\n'
    '      "quantity": string|null, "instructions": string|null,\n'
    '      "sets": integer|null, "reps": integer|null\n'
    "    }\n"
    "  ],\n"
    '  "warnings": [ "<anything illegible or uncertain>" ]\n'
    "}\n\n"
    "Rules:\n"
    "- Every item MUST have a `description`: this text is sent directly to an image/"
    "animation generator, so make it vivid and self-contained (1-2 sentences, in "
    "English). Describe WHO does WHAT with WHICH object/body part, plus enough "
    "concrete visual context (posture, where it is placed on the body, how it is "
    "held or used) for an illustrator to draw it without seeing the prescription. "
    "Do NOT include dosages, numbers, brand names, or schedule details in it. "
    "Examples: \"A person sits upright and places a clear oxygen mask over their "
    "nose and mouth, breathing calmly while a small oxygen concentrator runs beside "
    "them.\"; \"A person holds a glass of water in one hand and a single pill in the "
    "other, then places the pill in their mouth and swallows it.\"; \"A person "
    "slowly raises one arm overhead to stretch the shoulder, keeping the back "
    "straight.\"\n"
    "- Use `dosage`/`frequency`/`duration`/`quantity`/`instructions` for medications; "
    "leave `sets`/`reps` null for them.\n"
    "- Use `sets`/`reps` for physiotherapy exercises; leave medication fields null.\n"
    "- `prescription_type` is \"mixed\" only if there are both kinds of items.\n"
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
