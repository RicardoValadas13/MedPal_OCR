from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class Patient(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class Prescriber(BaseModel):
    name: Optional[str] = None


class FixedSchedule(BaseModel):
    """Used when the prescription specifies exact times (e.g. 'morning and night')."""

    type: Literal["fixed"]
    times: list[str] = Field(
        default_factory=list,
        description='Intake times in HH:MM (24h) format, e.g. ["08:00", "22:00"].',
    )
    days: list[Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]] = Field(
        default_factory=list,
        description="Days of the week the medication must be taken.",
    )
    take_with_food: bool = Field(
        False,
        description="True when the prescription says to take with food or after meals.",
    )


class IntervalSchedule(BaseModel):
    """Used when the prescription specifies a repeating interval (e.g. 'every 8 hours')."""

    type: Literal["interval"]
    interval_hours: int = Field(
        ...,
        description="Number of hours between doses, e.g. 8 for 'de 8 em 8 horas'.",
    )
    first_dose: str = Field(
        "08:00",
        description="Time of the first dose in HH:MM (24h) format.",
    )
    days: list[Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]] = Field(
        default_factory=list,
        description="Days of the week the medication must be taken.",
    )
    take_with_food: bool = Field(
        False,
        description="True when the prescription says to take with food or after meals.",
    )


MedicationSchedule = Annotated[
    Union[FixedSchedule, IntervalSchedule],
    Field(discriminator="type"),
]


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
    dosage: Optional[str] = Field(
        None,
        description="Amount per single intake only (e.g. '1 comprimido', '500 mg'). Never include frequency or timing.",
    )
    duration_days: Optional[int] = Field(
        None,
        description="Treatment duration as an integer number of days (e.g. 7 for '1 week', 30 for '1 month'). Null if not specified.",
    )
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
