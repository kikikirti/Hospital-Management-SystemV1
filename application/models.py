from datetime import datetime, date, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db=SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id =db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False, index = True)
    password_hash = db.Column(db.String(255), nullable=False)
    role=db.Column(db.String(10), nullable=False)  # 'admin', 'doctor', 'patient'
    is_active = db.Column(db.Boolean, default=True)


    doctor= db.relationship('Doctor', back_populates='user', uselist=False)
    patient= db.relationship('Patient', back_populates='user', uselist=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.id} name={self.name} role={self.role}>"
    


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)

    doctors = db.relationship('Doctor', back_populates='department', lazy="select")
    def __repr__(self):
        return f"<Department {self.id} {self.name}>"
    

class Doctor(db.Model):
    __tablename__='doctors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    specialization = db.Column(db.String(120))
    is_blacklisted = db.Column(db.Boolean, nullable=False, default=False)
    
    user = db.relationship('User', back_populates='doctor')
    department = db.relationship('Department', back_populates='doctors')
    appointments = db.relationship('Appointment', back_populates='doctor', lazy="select")

    def __repr__(self):
        return f"<Doctor {self.id} users={self.user_id} dept={self.department_id}>"
    

class Patient(db.Model):
    __tablename__='patients'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    medical_history = db.Column(db.Text)
    user=db.relationship('User', back_populates='patient')
    appointments = db.relationship('Appointment', back_populates='patient', lazy="select")
    is_blacklisted = db.Column(db.Boolean,nullable=False ,default=False)
    def __repr__(self):
        return f"<Patient {self.id} user={self.user_id}>"
    

# Status values: 'Booked', 'Completed', 'Cancelled'
class Appointment(db.Model):
    __tablename__='appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=True, index=True)
   
    appt_date = db.Column(db.Date, nullable=False, index=True)
    appt_time = db.Column(db.Time, nullable=False)
   
    status = db.Column(db.String(20), default='Booked', nullable=False)
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', back_populates='appointments')
    doctor = db.relationship('Doctor', back_populates='appointments')
    treatment= db.relationship('Treatment', back_populates='appointment', uselist=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'appt_date', 'appt_time', name='uq_doctor_appointment'),
    )
    def __repr__(self):
        d=self.appt_date.strftime("%Y-%m-%d") if isinstance(self.appt_date, date) else self.appt_date
        t=self.appt_time.strftime("%H:%M") if isinstance(self.appt_time, time) else self.appt_time
        return f"<Appointment {self.id} patient={self.patient_id} doctor={self.doctor_id} date={d} time={t} status={self.status}>"
    

class Treatment(db.Model):
    __tablename__='treatments'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='CASCADE'), unique=True, nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)

    appointment = db.relationship('Appointment', back_populates='treatment')

    def __repr__(self):
        return f"<Treatment {self.id} appointment={self.appointment_id}>"
    

class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False, index=True )
    avail_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    doctor= db.relationship('Doctor', backref=db.backref('availability', lazy='select', cascade='all, delete-orphan'))
    __table_args=(db.UniqueConstraint('doctor_id', 'avail_date', 'start_time', 'end_time', name='uq_doctor_availability_slot'),)

    def __repr__(self):
        s=self.start_time.strftime('%H:%M')
        e=self.end_time.strftime('%H:%M')
        return f"<DoctorAvailability {self.id} doctor={self.doctor_id} date={self.avail_date} {s}-{e}>"