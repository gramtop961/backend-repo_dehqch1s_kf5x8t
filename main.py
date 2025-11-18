import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Medical Booking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class IDModel(BaseModel):
    id: str


def ensure_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")


@app.get("/")
def read_root():
    return {"message": "Medical Booking Backend is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Public endpoints for hospitals, clinics, doctors, appointments

@app.get("/api/hospitals")
def list_hospitals():
    items = get_documents("hospital")
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items


class HospitalCreate(BaseModel):
    name: str
    city: str
    address: str
    phone: Optional[str] = None


@app.post("/api/hospitals", status_code=201)
def create_hospital(payload: HospitalCreate):
    hid = create_document("hospital", payload.model_dump())
    return {"id": hid}


@app.get("/api/clinics")
def list_clinics(hospital_id: Optional[str] = None):
    filter_q = {}
    if hospital_id:
        filter_q = {"hospital_id": hospital_id}
    items = get_documents("clinic", filter_q)
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items


class ClinicCreate(BaseModel):
    hospital_id: str
    name: str
    specialties: List[str] = []


@app.post("/api/clinics", status_code=201)
def create_clinic(payload: ClinicCreate):
    # Validate hospital id format; existence check optional
    ensure_object_id(payload.hospital_id)
    cid = create_document("clinic", payload.model_dump())
    return {"id": cid}


@app.get("/api/doctors")
def list_doctors(clinic_id: Optional[str] = None, specialty: Optional[str] = None):
    q = {}
    if clinic_id:
        q["clinic_id"] = clinic_id
    if specialty:
        q["specialty"] = specialty
    items = get_documents("doctor", q)
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items


class DoctorCreate(BaseModel):
    clinic_id: str
    name: str
    specialty: str
    days_available: List[str] = []
    time_slots: List[str] = []


@app.post("/api/doctors", status_code=201)
def create_doctor(payload: DoctorCreate):
    ensure_object_id(payload.clinic_id)
    did = create_document("doctor", payload.model_dump())
    return {"id": did}


@app.get("/api/appointments")
def list_appointments(doctor_id: Optional[str] = None, date: Optional[str] = None):
    q = {}
    if doctor_id:
        q["doctor_id"] = doctor_id
    if date:
        q["date"] = date
    items = get_documents("appointment", q)
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items


class AppointmentCreate(BaseModel):
    patient_name: str
    patient_phone: str
    doctor_id: str
    date: str
    time_slot: str


@app.post("/api/appointments", status_code=201)
def create_appointment(payload: AppointmentCreate):
    ensure_object_id(payload.doctor_id)
    # Basic duplicate check for same doctor/time
    existing = get_documents("appointment", {
        "doctor_id": payload.doctor_id,
        "date": payload.date,
        "time_slot": payload.time_slot
    })
    if existing:
        raise HTTPException(status_code=409, detail="This slot is already booked")

    aid = create_document("appointment", {
        **payload.model_dump(),
        "status": "pending"
    })
    return {"id": aid, "status": "pending"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
