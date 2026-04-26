from app.core.database import Base, engine

# Import ALL models so SQLAlchemy registers them before creating tables
from app.features.patients.models import Patient
from app.features.queue.models import QueueEntry
from app.features.auth.models import User, Clinic
from app.features.consultations.models import Consultation
from app.features.prescriptions.models import Prescription, PrescriptionMedicine



def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    print("   Tables: patients, queue_entries, users, clinics, consultations, prescriptions, prescription_medicines")


if __name__ == "__main__":
    init_db()
