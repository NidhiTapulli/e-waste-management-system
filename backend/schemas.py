from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
import re

ALLOWED_STATUSES = ["Pending", "Scheduled", "Collected", "Processed"]
ALLOWED_CONDITIONS = ["Working", "Semi-functional", "Non-functional / Scrap"]
DEFAULT_CATEGORIES = [
    "Mobile Phones",
    "Laptops",
    "Computers",
    "Televisions",
    "Batteries",
    "Home Appliances",
    "Other Electronics"
]


class RequestCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Customer full name")
    email: str = Field(..., min_length=5, max_length=120, description="Customer email address")
    phone: str = Field(..., min_length=7, max_length=15, description="Contact phone number")
    address: str = Field(..., min_length=5, max_length=250, description="Pickup street address")
    city: str = Field(..., min_length=2, max_length=60, description="City")
    pincode: str = Field(..., min_length=3, max_length=12, description="Postal / ZIP / PIN code")
    category: str = Field(..., min_length=2, max_length=60, description="Electronic item category")
    item_description: str = Field(..., min_length=2, max_length=500, description="Item details, brand, model")
    quantity: int = Field(default=1, ge=1, le=1000, description="Quantity of items")
    condition: str = Field(default="Used", description="Condition of the item")
    preferred_date: str = Field(..., min_length=8, max_length=12, description="Preferred pickup date (YYYY-MM-DD)")
    special_notes: Optional[str] = Field(default="", max_length=500, description="Optional pickup notes")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        pattern = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$"
        if not re.match(pattern, v):
            raise ValueError("Please provide a valid email address.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        digits = re.sub(r"[^\d+]", "", v)
        if len(digits) < 7:
            raise ValueError("Phone number must contain at least 7 digits.")
        return digits

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        v = v.strip()
        if v not in ALLOWED_CONDITIONS and v != "Used":
            raise ValueError(f"Condition must be one of {ALLOWED_CONDITIONS}")
        return v


class RequestUpdateStatus(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.strip()
        if v not in ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of {', '.join(ALLOWED_STATUSES)}")
        return v


class RequestResponse(BaseModel):
    id: int
    tracking_id: str
    full_name: str
    email: str
    phone: str
    address: str
    city: str
    pincode: str
    category: str
    item_description: str
    quantity: int
    condition: str
    preferred_date: str
    special_notes: Optional[str] = ""
    status: str
    created_at: str
    updated_at: str


class DashboardStats(BaseModel):
    total_requests: int
    pending: int
    scheduled: int
    collected: int
    processed: int
    category_counts: Dict[str, int]
    recent_activity: List[RequestResponse]


# Authentication Schemas
class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        pattern = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$"
        if not re.match(pattern, v):
            raise ValueError("Please provide a valid email address.")
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
