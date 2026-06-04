from typing import Literal, Optional

from pydantic import BaseModel, Field


class Patient(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class Prescriber(BaseModel):
    name: Optional[str] = None


class MedicationSchedule(BaseModel):
    times: list[str] = Field(
        default_factory=list,
        description='List of intake times in HH:MM (24h) format, e.g. ["08:00", "20:00"].',
    )
    days: list[Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]] = Field(
        default_factory=list,
        description="Days of the week the medication should be taken.",
    )
    take_with_food: bool = Field(
        False,
        description="True when the prescription says to take with food or after meals.",
    )


class PrescriptionItem(BaseModel):
    type: Literal["medication", "physiotherapy"]
    name: str = Field(..., description="Drug name (with strength) or exercise name.")
    # The action prompt consumed by the GIF Generation API as its `action` field.
    description: str = Field(
        ...,
        description=(
            "Vivid 1-2 sentence visual instruction used as the image-generation "
            "prompt; no dosages or numbers."
        ),
    )

    # Medication-specific fields (null for physiotherapy items).
    dosage: Optional[str] = Field(None, description="Amount per single intake only (e.g. '1 comprimido', '2 pulverizações em cada narina'). Never include frequency or timing.")
    frequency: Optional[str] = Field(None, description="How often the medication is taken (e.g. '3 vezes por dia', 'de 8 em 8 horas'). Never include the dose amount.")
    duration: Optional[str] = Field(None, description="Treatment period as written on the prescription (e.g. '5 dias', '1 semana').")
    duration_days: Optional[int] = Field(
        None,
        description="Duration expressed as an integer number of days (e.g. 7 for '1 week', 30 for '1 month'). Null if not specified.",
    )
    quantity: Optional[str] = None
    instructions: Optional[str] = None
    schedule: Optional[MedicationSchedule] = None

    # Physiotherapy-specific fields (null for medication items).
    sets: Optional[int] = None
    reps: Optional[int] = None


class PrescriptionResponse(BaseModel):
    prescription_type: Literal["medication", "physiotherapy", "mixed"]
    language: str = Field("en", description="Detected language of the document (ISO code).")
    patient: Optional[Patient] = None
    prescriber: Optional[Prescriber] = None
    date: Optional[str] = None
    items: list[PrescriptionItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Base64ImageRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image bytes (no data URI prefix needed).")
    mime_type: str = Field("image/jpeg", description="MIME type of the encoded image.")
