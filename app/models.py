from typing import Literal, Optional

from pydantic import BaseModel, Field


class Patient(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class Prescriber(BaseModel):
    name: Optional[str] = None


class PrescriptionItem(BaseModel):
    type: Literal["medication", "physiotherapy"]
    name: str = Field(..., description="Drug name (with strength) or exercise name.")
    # The action string consumed by the GIF Generation API as its `action` field.
    description: str = Field(
        ...,
        description="Short imperative action depicting this item, e.g. 'take this pill'.",
    )

    # Medication-specific fields (null for physiotherapy items).
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    quantity: Optional[str] = None
    instructions: Optional[str] = None

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
