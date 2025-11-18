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


# --------------------------------------------------
# Development utility: seed sample data
# --------------------------------------------------
class SeedResponse(BaseModel):
    hospitals: int
    clinics: int
    doctors: int


def _seed_dev_data() -> SeedResponse:
    """Insert a small set of sample hospitals, clinics, and doctors if empty."""
    # Only seed if there are no hospitals yet
    existing_hospitals = get_documents("hospital")
    if existing_hospitals:
        return SeedResponse(hospitals=0, clinics=0, doctors=0)

    # Hospitals
    h_ids: List[str] = []
    demo_hospitals = [
        {"name": "مستشفى الشفاء", "city": "الرياض", "address": "حي العليا، شارع رقم 10", "phone": "+966500000001"},
        {"name": "مستشفى الندى", "city": "جدة", "address": "حي الروضة، طريق الملك", "phone": "+966500000002"},
        {"name": "مركز الرحمة الطبي", "city": "الدمام", "address": "حي المزروعية، شارع الأمير", "phone": "+966500000003"},
    ]
    for h in demo_hospitals:
        h_id = create_document("hospital", h)
        h_ids.append(h_id)

    # Clinics per hospital
    clinic_ids: List[str] = []
    demo_clinics = [
        (h_ids[0], [
            {"name": "قسم الباطنية", "specialties": ["باطنية", "سكري"]},
            {"name": "عيادة القلب", "specialties": ["قلب"]},
        ]),
        (h_ids[1], [
            {"name": "عيادة الأطفال", "specialties": ["أطفال", "تغذية"]},
            {"name": "عيادة العظام", "specialties": ["عظام"]},
        ]),
        (h_ids[2], [
            {"name": "عيادة الأسنان", "specialties": ["أسنان"]},
        ]),
    ]
    for hid, clinics in demo_clinics:
        for c in clinics:
            cid = create_document("clinic", {"hospital_id": hid, **c})
            clinic_ids.append(cid)

    # Doctors per clinic
    demo_doctors = [
        {"clinic_id": clinic_ids[0], "name": "د. أحمد السالم", "specialty": "باطنية", "days_available": ["Sat","Mon","Wed"], "time_slots": ["09:00","09:30","10:00","10:30","11:00"]},
        {"clinic_id": clinic_ids[0], "name": "د. منى علي", "specialty": "سكري", "days_available": ["Sun","Tue"], "time_slots": ["12:00","12:30","13:00","13:30","14:00"]},
        {"clinic_id": clinic_ids[1], "name": "د. خالد مراد", "specialty": "قلب", "days_available": ["Mon","Thu"], "time_slots": ["09:00","09:30","10:00"]},
        {"clinic_id": clinic_ids[2], "name": "د. سارة يوسف", "specialty": "أطفال", "days_available": ["Sat","Sun","Mon"], "time_slots": ["11:00","11:30","12:00"]},
        {"clinic_id": clinic_ids[3], "name": "د. فهد السبيعي", "specialty": "عظام", "days_available": ["Tue","Wed"], "time_slots": ["09:00","09:30","10:00","10:30"]},
        {"clinic_id": clinic_ids[4], "name": "د. ليلى القحطاني", "specialty": "أسنان", "days_available": ["Sat","Thu"], "time_slots": ["09:00","09:30","10:00","10:30","11:00","11:30"]},
    ]
    for d in demo_doctors:
        create_document("doctor", d)

    return SeedResponse(hospitals=len(h_ids), clinics=len(clinic_ids), doctors=len(demo_doctors))


@app.post("/api/seed", response_model=SeedResponse)
def seed_dev_data():
    """Seed the database with sample data. Safe to call multiple times."""
    return _seed_dev_data()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
