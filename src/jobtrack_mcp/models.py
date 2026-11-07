"""Define the domain models for Jobtrack"""

from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, field_validator

class ApplicationStatus(StrEnum):
    """Represent the possible statuses of a job application"""

    WISHLIST = "wishlist"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(BaseModel):
    """Represent a job application stored in a database.
    
    Attributes:
        id: Unique database identifier
        company: Name of the comapany
        role: Job position or title
        status: Current applications status
        job_url: URL of job posting (optional)
        notes: Additional notes about application (optinal)
        applied_on: Date of the application submission
        created_at: UTC timestamp when the record was created
        updated_at: UTC timestamp when the record was last updated
    """

    id: int
    company: str
    role: str
    status: ApplicationStatus=ApplicationStatus.WISHLIST
    job_url: str | None = None
    notes: str | None = None
    applied_on: date | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("company", "role")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        """Strip whitespace and reject empty company names or roles."""

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty.")

        return value


    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_utc_timestamp(cls, value: datetime) -> datetime:
        """Normalize timestamps to timezone-aware UTC."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware.")

        return value.astimezone(timezone.utc)