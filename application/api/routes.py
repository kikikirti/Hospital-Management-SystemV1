from datetime import datetime, date, time
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from application.models import db, User, Doctor, Patient, Appointment, Treatment
from application.controllers import role_required

api_bp = Blueprint('api', __name__, url_prefix='/api')


# Helper functions

def doctor_to_dict(doctor):
    return {
        'id': doctor.id,
        'name': doctor.user.name if doctor.user else None,
        'email': doctor.user.email if doctor.user else None,
        'specialization': doctor.specialization,
        'department': doctor.department.name if doctor.department else None,
        'is_blacklisted': bool(doctor.is_blacklisted),
    }

def patient_to_dict(patient):
    return {
        'id': patient.id,
        'name': patient.user.name if patient.user else None,
        'email': patient.user.email if patient.user else None,
        'phone': patient.phone,
        'address': patient.address,
        'age': patient.age,
        'gender': patient.gender,
        'is_blacklisted': bool(patient.is_blacklisted),
    }

def treatment_to_dict(t: Treatment | None):
    if not t:
        return None
    return {
        "id": t.id,
        "diagnosis": t.diagnosis,
        "prescription": t.prescription,
        "notes": t.notes,
    }

def appointment_to_dict(a: Appointment):
    return {
            "id": a.id,
            "date": a.appt_date.isoformat() if a.appt_date else None,
            "time": a.appt_time.strftime("%H:%M") if a.appt_time else None,
            "status": a.status,
            "note": a.notes,
            "doctor_id": a.doctor_id,
            "doctor_name": a.doctor.user.name if a.doctor and a.doctor.user else None,
            "patient_id": a.patient_id,
            "patient_name": a.patient.user.name if a.patient and a.patient.user else None,
            "treatment": treatment_to_dict(a.treatment),
        }

def bad_request(message, status_code=400):
    response = jsonify({'error': message})
    response.status_code = status_code
    return response

#**************************************
#===========API ROUTES=================
#**************************************

#------Doctor API--------

@api_bp.route('/doctors', methods=['GET'])
@login_required
def api_list_doctors():
    q= (request.args.get('q') or '').strip()
    query=Doctor.query.join(User)
    if q:
        like=f"%{q}%"
        query=query.filter(or_(User.name.ilike(like), Doctor.specialization.ilike(like)))
    doctors=query.order_by(User.name.asc()).all()
    return jsonify([doctor_to_dict(d) for d in doctors])

@api_bp.route('/doctors/<int:doctor_id>', methods=['GET'])
@login_required
def api_get_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return jsonify(doctor_to_dict(doctor))

#------Patient API--------

@api_bp.route('/patients', methods=['GET'])
@login_required
def api_get_current_patient():
    pat=current_user.patient
    if not pat:
        abort(404)
    return jsonify(patient_to_dict(pat))

@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
@login_required
def api_get_patient(patient_id):
    patient=Patient.query.get_or_404(patient_id)
    if current_user.role =='admin':
        return jsonify(patient_to_dict(patient))
    
    if current_user.role =='patient' and current_user.patient and current_user.patient.id == patient.id:
        return jsonify(patient_to_dict(patient))

    abort(404)

#------Appointment API--------

@api_bp.route('/appointments', methods=['GET'])
@login_required
def api_list_appointments():
    status_filter = request.args.get('status', '').strip()
    if current_user.role == 'admin':
        q=Appointment.query
    elif current_user.role == 'doctor' and current_user.doctor:
        q=Appointment.query.filter_by(doctor_id=current_user.doctor.id)
    elif current_user.role == 'patient' and current_user.patient:
        q=Appointment.query.filter_by(patient_id=current_user.patient.id)
    else:
        return bad_request("Unsupported role for appointments listing", 403)
    if status_filter:
        q=q.filter(Appointment.status==status_filter)
    appts=q.order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc()).all()
    return jsonify([appointment_to_dict(a) for a in appts])

@api_bp.route('/appointments', methods=['POST'])
@login_required
@role_required("patient")
def api_create_appointment():
    data=request.get_json(silent=True) or {}
    doctor_id=data.get('doctor_id')
    date_str=data.get('date')
    time_str=data.get('time')

    if not doctor_id or not date_str or not time_str:
        return bad_request("doctor_id, date, and time are required")
    
    doctor=Doctor.query.get(doctor_id)
    if not doctor or doctor.is_blacklisted:
        return bad_request("Doctor not available", 400)
    
    try:
        appt_date=date.fromisoformat(date_str)
        appt_time=datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return bad_request("Invalid date or time format")

    if appt_date<=date.today():
        return bad_request("Appointment date must be in the future")
    
    pat=current_user.patient
    if not pat:
        return bad_request("Patient profile not found", 400)
    
    appt=Appointment(
        patient_id=pat.id,
        doctor_id=doctor.id,
        appt_date=appt_date,
        appt_time=appt_time,
        status='Booked'
    )
    db.session.add(appt)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return bad_request("The selected time slot is not available", 400)
    except Exception as e:
        db.session.rollback()
        return bad_request("Failed to create appointment", 500)
    return jsonify(appointment_to_dict(appt)), 201

@api_bp.route('/appointments/<int:appt_id>', methods=['GET'])
@login_required
def api_get_appointment(appt_id):
    appt=Appointment.query.get_or_404(appt_id)
    if current_user.role =='admin':
        return jsonify(appointment_to_dict(appt))
    
    if current_user.role =='doctor' and current_user.doctor and appt.doctor_id == current_user.doctor.id:
        return jsonify(appointment_to_dict(appt))
    
    if current_user.role =='patient' and current_user.patient and appt.patient_id == current_user.patient.id:
        return jsonify(appointment_to_dict(appt))
    
    abort(403)


@api_bp.route('/appointments/<int:appt_id>', methods=['PATCH'])
@login_required
def api_update_appointment_status(appt_id):
    appt=Appointment.query.get_or_404(appt_id)
    data=request.get_json(silent=True) or {}
    new_status=data.get('status')

    if new_status not in {'Booked', 'Completed', 'Cancelled'}:
        return bad_request("Invalid status")
    
    # Authorization check
    if current_user.role =='admin':
        allowed=True
    elif current_user.role =='doctor' and current_user.doctor and appt.doctor_id == current_user.doctor.id:
        allowed=True
    elif current_user.role =='patient' and current_user.patient and appt.patient_id == current_user.patient.id:
        if new_status =='Cancelled' and appt.status =='Booked':
            allowed=True
        else:
            return bad_request("Patients can only cancel their booked appointments", 403)
    else:
        return bad_request("You are not authorized to update this appointment", 403)
    
    if appt.status =='Completed' and new_status =='Booked':
        return bad_request("Cannot revert a completed appointment to booked via api, contact admin", 400)
    appt.status=new_status
    db.session.commit()
    return jsonify(appointment_to_dict(appt))

@api_bp.route('/appointments/<int:appt_id>', methods=['DELETE'])
@login_required
def api_delete_appointment(appt_id):
    appt=Appointment.query.get_or_404(appt_id)
    
    if current_user.role =='admin':
        allowed=True
    elif current_user.role =='doctor' and current_user.doctor and appt.doctor_id == current_user.doctor.id:
        allowed=True
    elif current_user.role =='patient' and current_user.patient and appt.patient_id == current_user.patient.id:
        if appt.appt_date > date.today() and appt.status =='Booked':
            allowed=True
        else:
            return bad_request("Patients can only cancel their upcoming booked appointments", 403)
    else:
        return bad_request("You are not authorized to delete this appointment", 403)
    db.session.delete(appt)
    db.session.commit()
    return jsonify({"deleted": True,"id": appt_id})