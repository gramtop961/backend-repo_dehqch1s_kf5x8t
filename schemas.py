"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Example schemas (you can still use these if needed):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# --------------------------------------------------
# Medical booking app schemas (collections)
# --------------------------------------------------

class Hospital(BaseModel):
    name: str = Field(..., description="Hospital name")
    city: str = Field(..., description="City")
    address: str = Field(..., description="Full address")
    phone: Optional[str] = Field(None, description="Contact phone number")

class Clinic(BaseModel):
    hospital_id: str = Field(..., description="Related hospital ObjectId as string")
    name: str = Field(..., description="Clinic/Department name")
    specialties: List[str] = Field(default_factory=list, description="List of specialties")

class Doctor(BaseModel):
    clinic_id: str = Field(..., description="Related clinic ObjectId as string")
    name: str = Field(..., description="Doctor's full name")
    specialty: str = Field(..., description="Doctor specialty")
    days_available: List[str] = Field(default_factory=list, description="Days doctor works e.g., ['Sat','Sun','Mon']")
    time_slots: List[str] = Field(default_factory=lambda: [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30"
    ], description="Daily time slots")

class Appointment(BaseModel):
    patient_name: str = Field(..., description="Patient full name")
    patient_phone: str = Field(..., description="Patient contact phone")
    doctor_id: str = Field(..., description="Doctor ObjectId as string")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time_slot: str = Field(..., description="Selected time slot e.g., 10:30")
    status: str = Field("pending", description="Status: pending/confirmed/cancelled")

# Note: The Flames database viewer can read these schemas from GET /schema endpoint
# and help with ad-hoc CRUD if needed.
