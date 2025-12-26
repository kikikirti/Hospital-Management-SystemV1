from functools import wraps
from flask import request, redirect, url_for, flash, session, Blueprint, render_template, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, cast, String, and_, func
from application.models import *
from application.forms import *
from datetime import datetime, timedelta, date
from sqlalchemy.exc import IntegrityError
from wtforms.validators import Optional

# --------------------------------------------------------
# ------- Authentication Blueprint ------- 
# --------------------------------------------------------
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# role guard

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                return "Forbidden", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

@auth_bp.route("/") # Redirect based on role
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        else: 
            return redirect(url_for('patient.dashboard'))
    return render_template('home.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form=LoginForm()
    if request.method =='POST' and form.validate_on_submit():
        email=form.email.data.strip().lower()
        password=form.password.data
        user=User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password","danger")
            return render_template('login.html', form=form)
        if not user.is_active:
            flash("Account is inactive. Contact admin.","warning")
            return redirect(url_for('auth.login'))
        
        if user.role == 'patient':
            if not getattr(user, 'patient', None):
                flash("Patient profile not found. Contact admin.","danger")
                return redirect(url_for('auth.login'))
            if user.patient.is_blacklisted:
                flash("Your account is blacklisted. Contact admin.","danger")
                return redirect(url_for('auth.login'))
        if user.role == 'doctor':
            if getattr(user, 'doctor', None) and user.doctor.is_blacklisted:
                flash("Doctor account is blacklisted. Contact admin.","danger")
                return redirect(url_for('auth.login'))


        login_user(user)
        flash("Login successful","success")

        # Redirect based on role
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        else: 
            return redirect(url_for('patient.dashboard'))
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully","success")
    return redirect(url_for('auth.login'))

# Registration route for patients only
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form=RegisterForm()
    if request.method =='POST' and form.validate_on_submit():
        name=form.name.data.strip()
        email=form.email.data.strip().lower()
        password=form.password.data
        
        existing=User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered","danger")
            return render_template('register.html', form=form)
        
        user=User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role="patient", 
            is_active=True
        )
        db.session.add(user)
        db.session.flush()  # Flush to get user.id
        patient=Patient(user_id=user.id)
        db.session.add(patient)
        db.session.commit()
        flash("Registration successful. Please log in.","success")
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

# --------------------------------------------------------
# ------- Admin Blueprint -------  
# --------------------------------------------------------

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
# Helper to get or create department
def _get_or_create_department(name:str):
    if not name:
        return None
    dept = Department.query.filter_by(name=name.strip()).first() # Check if department exists
    if not dept:
        dept = Department(name=name.strip())
        db.session.add(dept)
        db.session.commit()
    return dept

def _populate_department_choices(form):
    departments=Department.query.order_by(Department.name.asc()).all()
    choices=[(0,"-- No department--")]
    choices+=[(dept.id,dept.name) for dept in departments]
    form.department.choices=choices

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    booked_appts = Appointment.query.filter_by(status='Booked').count()
    completed_appts=Appointment.query.filter_by(status='Completed').count()
    cancelled_appts=Appointment.query.filter_by(status='Cancelled').count()

    status_labels = ["Booked", "Completed", "Cancelled"]
    status_values = [booked_appts, completed_appts, cancelled_appts]


    return render_template('admin_dashboard.html', total_doctors=total_doctors, total_patients=total_patients, total_appts=total_appointments, booked_appts=booked_appts,completed_appts=completed_appts, status_labels=status_labels, status_values=status_values, cancelled_appts=cancelled_appts)

@admin_bp.route('/doctors')
@login_required
@role_required('admin')
def doctors_list():
    q=request.args.get('q','').strip()
    query=db.session.query(Doctor).join(User)
    if q:
        query=query.filter(or_(User.name.ilike(f'%{q}%'), Doctor.specialization.ilike(f'%{q}%')))
    doctors=query.order_by(User.id.asc()).all()
    form=SearchForm(q=q)
    return render_template('admin_doctors_list.html', doctors=doctors, form=form)

@admin_bp.route('/doctors/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def doctor_create():
    form= DoctorCreateForm()
    _populate_department_choices(form)

    if form.validate_on_submit():
        name=form.name.data.strip()
        email=form.email.data.strip()
        user=User(name=form.name.data.strip(), email=form.email.data.strip(), role='doctor')
        user.password_hash=generate_password_hash(form.password.data)
        db.session.add(user)
        db.session.flush()

        department_id=form.department.data or 0
        if department_id ==0:
            department_id=None
        doctor=Doctor(user_id=user.id, department_id=department_id, specialization=form.specialization.data.strip() or None)
        db.session.add(doctor)
        db.session.commit()
        flash('Doctor created successfully', 'success')
        return redirect(url_for('admin.doctors_list'))
    return render_template('admin_doctors_form.html', form=form, mode="create")

# edit doctor
@admin_bp.route('/doctors/<int:doctor_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def doctor_edit(doctor_id):
    doctor=Doctor.query.get_or_404(doctor_id)
    form=DoctorForm()
    user=doctor.user
    _populate_department_choices(form)
    
    if form.validate_on_submit():
        user.name=form.name.data.strip()
        user.email=form.email.data.strip()

        if form.password.data and form.password.data.strip() != "":
            user.password_hash=generate_password_hash(form.password.data)

        doctor.specialization=form.specialization.data.strip() or None
        department_id=form.department.data or 0
        doctor.department_id=department_id if department_id!=0 else None
        db.session.commit()
        flash('Doctor updated successfully', 'success')
        return redirect(url_for('admin.doctors_list'))

    if request.method == "GET":
        form.name.data=user.name
        form.email.data=user.email
        form.specialization.data=doctor.specialization
        form.department.data=doctor.department_id or 0
        form.password.data=""

    return render_template('admin_doctors_form.html', form=form, mode="edit")


# delelte doctor
@admin_bp.route('/doctors/<int:doctor_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def doctor_delete(doctor_id):
    doctor=Doctor.query.get_or_404(doctor_id)
    user=doctor.user
    if getattr(doctor, "appointments", None) and len(doctor.appointments) > 0:
        flash("Cannot delete doctor with appointments."
              "Please cancel/reassign all appointments first or use blaklist instead.",
              "danger")
        return redirect(url_for('admin.doctors_list'))
    db.session.delete(doctor)
    db.session.delete(user)
    db.session.commit()
    flash("Doctor deleted successfully","success")
    return redirect(url_for('admin.doctors_list'))

# toggle blacklist
@admin_bp.route('/doctors/<int:doctor_id>/toggle_blacklist', methods=['POST'])
@login_required 
@role_required('admin')
def doctor_blacklist(doctor_id):
    doc=Doctor.query.get_or_404(doctor_id)
    doc.is_blacklisted=not doc.is_blacklisted
    db.session.commit()
    flash(f"Doctor blacklist status: {'Blacklisted' if doc.is_blacklisted else 'Active'}","success")
    return redirect(url_for('admin.doctors_list'))

# patients list and search
@admin_bp.route('/patients')
@login_required
@role_required('admin')
def patients_list():
    q=request.args.get('q','').strip()
    query=db.session.query(Patient).join(User)
    if q:
        query=query.filter(or_(
            User.name.ilike(f'%{q}%'), 
            User.email.ilike(f'%{q}%'),
            cast(Patient.id, String).ilike(f'%{q}%'),
            Patient.phone.ilike(f'%{q}%')))
    patients=query.order_by(User.id.asc()).all()
    form=SearchForm(q=q)
    return render_template('admin_patients_list.html', patients=patients, form=form)

# create patient
@admin_bp.route('/patients/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def patient_create():
    form=PatientForm()
    if request.method =="POST" and form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.strip().lower()).first():
            flash("Email already registered","danger")
            return render_template('patient_form.html', form=form, mode="create")
        user=User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            password_hash=generate_password_hash(form.password.data),
            role="patient",
            is_active=True
        )
        db.session.add(user)
        db.session.flush()  # Flush to get user.id

        patient=Patient(
            user_id=user.id,
            gender=form.gender.data,
            age=form.age.data,
            address=form.address.data.strip() if form.address.data else None,
            phone=form.phone.data.strip() if form.phone.data else None,
            medical_history=form.medical_history.data.strip() if form.medical_history.data else None

        )
        db.session.add(patient)
        db.session.commit()
        flash("Patient created successfully","success")
        return redirect(url_for('admin.patients_list'))
    return render_template('patient_form.html', form=form, mode="create")

# edit patient
@admin_bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def patient_edit(patient_id):
    patient=Patient.query.get_or_404(patient_id)
    user=patient.user
    form=PatientForm(
        name=user.name,
        email=user.email,
        phone=patient.phone or '',
        address=patient.address or '',
        age=patient.age,
        gender=patient.gender or '',
        medical_history=patient.medical_history or ''
    )
    form.password.validators=[] 
    if request.method=='POST' and form.validate_on_submit():
        email=form.email.data.strip().lower()
        existing=User.query.filter(User.email==email, User.id!=user.id).first()
        if existing:
            flash("Email already registered with another user","danger")
            return render_template('patient_form.html', form=form, mode="edit")
        
        user.name=form.name.data.strip()
        user.email=email
        if form.password.data:
            user.password_hash=generate_password_hash(form.password.data)
        patient.phone=form.phone.data.strip() if form.phone.data else None
        patient.address=form.address.data.strip() if form.address.data else None   
        patient.age=form.age.data
        patient.gender=form.gender.data.strip() if form.gender.data else None
        patient.medical_history=form.medical_history.data.strip() if form.medical_history.data else None
        db.session.commit()
        flash("Patient updated successfully","success")
        return redirect(url_for('admin.patients_list'))
    return render_template('patient_form.html', form=form, mode="edit")

# delete patient
@admin_bp.route('/patients/<int:patient_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def patient_delete(patient_id):
    patient=Patient.query.get_or_404(patient_id)
    if patient.appointments and len(patient.appointments)>0:
        flash("Patient has appointments, cannot be deleted","danger")
        return redirect(url_for('admin.patients_list'))
    
    user=patient.user
    db.session.delete(patient)
    db.session.delete(user)
    db.session.commit()
    flash("Patient deleted successfully","success")
    return redirect(url_for('admin.patients_list'))

# blacklist patient
@admin_bp.route('/patients/<int:patient_id>/toggle_blacklist', methods=['POST'])
@login_required 
@role_required('admin')
def patient_blacklist(patient_id):
    pat=Patient.query.get_or_404(patient_id)
    pat.is_blacklisted=not bool(pat.is_blacklisted)
    db.session.commit()
    flash(f"Patient blacklist Status={pat.is_blacklisted}","success")
    return redirect(url_for('admin.patients_list'))

# Appointments list
@admin_bp.route('/appointments')
@login_required
@role_required('admin')
def appointments_list():
    q=request.args.get("q","").strip().lower()
    appointments= Appointment.query.order_by(Appointment.appt_date.desc(),Appointment.appt_time.desc()).all()
    if q:
        results=[]
        for a in appointments:
            doctor_name=a.doctor.user.name.lower() if a.doctor and a.doctor.user and a.doctor.user.name else ""
            patient_name=a.patient.user.name.lower() if a.patient and a.patient.user and a.patient.user.name else ""
            status=(a.status or "").lower()
            date_str=a.appt_date.isoformat() if a.appt_date else ""
            if (
                q in doctor_name or
                q in patient_name or
                q in status or
                q in date_str
            ):
                results.append(a)
        appointments=results
    return render_template('admin_appointments_list.html', appointments=appointments, q=q)

# Appointment set status
@admin_bp.route('/appointments/<int:appt_id>/status', methods=['POST'])
@login_required
@role_required('admin')
def appointment_set_status(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    new_status = (request.form.get('status') or "").strip()  # Booked, Completed, Cancelled

    if new_status not in {"Booked", "Completed", "Cancelled"}:
        flash("Invalid status", "danger")
        return redirect(url_for('admin.appointments_list'))

    if appt.status == "Completed" and new_status == "Cancelled":
        flash("Completed appointments cannot be cancelled.", "danger")
        return redirect(url_for('admin.appointments_list'))

    appt.status = new_status
    db.session.commit()
    flash(f"Appointment {appt_id} status set to {new_status}", "success")
    return redirect(url_for('admin.appointments_list'))

# Appointment delete
@admin_bp.route('/appointments/<int:appt_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def appointment_delete(appt_id):
    appt=Appointment.query.get_or_404(appt_id)
    db.session.delete(appt)
    db.session.commit()
    flash(f"Appointment {appt_id} deleted","success")
    return redirect(url_for('admin.appointments_list'))

# Department List and create
@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def department_list():
    form=DepartmentForm()
    if form.validate_on_submit():
        name=form.name.data.strip()
        desc=(form.description.data or '').strip() or None

        existing=Department.query.filter(db.func.lower(Department.name)==name.lower()).first()
        if existing:
            flash("Department already exists","warning")
        else:
            dept=Department(name=name,description=desc)
            db.session.add(dept)
            db.session.commit()
            flash(f"Department {dept.name} created","success")
            return redirect(url_for('admin.department_list'))

    departments=Department.query.order_by(Department.name.asc()).all()
    return render_template('admin_departments_list.html',form=form,departments=departments)

@admin_bp.route('/department/<int:dept_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def department_delete(dept_id):
    dept=Department.query.get_or_404(dept_id)
    if getattr(dept,"doctors",None) and len(dept.doctors)>0:
        flash(f"Cannot delete department {dept.name} because it has doctors","danger")
        return redirect(url_for('admin.department_list'))
    db.session.delete(dept)
    db.session.commit()
    flash(f"Department {dept.name} deleted","success")
    return redirect(url_for('admin.department_list'))


# --------------------------------------------------------
# ------- Doctor Blueprint -------  
# --------------------------------------------------------

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

# Helper function
def _require_doctor_and_get():
    if not current_user.is_authenticated or current_user.role != 'doctor':
        abort(403)
    if not current_user.doctor:
        abort(403)
    return current_user.doctor

# Doctor dashboard  
@doctor_bp.route('/dashboard')
@login_required
@role_required('doctor')
def dashboard():
    doctor=_require_doctor_and_get()
    today=date.today()
    start_week=today-timedelta(days=today.weekday())
    end_week=start_week+timedelta(days=6)

    today_appointments=Appointment.query.filter_by(doctor_id=doctor.id).filter(Appointment.appt_date==today).order_by(Appointment.appt_date.asc(), Appointment.appt_time.asc()).all()
    weekly_appointments=Appointment.query.filter_by(doctor_id=doctor.id).filter(Appointment.appt_date.between(start_week,end_week)).filter(Appointment.status=='Booked').order_by(Appointment.appt_date.asc(), Appointment.appt_time.asc()).all()
    
    patients = (db.session.query(Patient).join(User, Patient.user_id == User.id).join(Appointment, Appointment.patient_id == Patient.id).filter(Appointment.doctor_id == doctor.id).group_by(Patient.id, User.name).order_by(User.name.asc()).limit(10).all())

    # For chart data(appointment status distribution)
    status_rows=(db.session.query(Appointment.status,func.count(Appointment.id)).filter(Appointment.doctor_id == doctor.id).group_by(Appointment.status).all())
    status_labels=[]
    status_values=[]
    for status, count in status_rows:
        if count and count>0:
            status_labels.append(status)
            status_values.append(count)
    
    return render_template('doctor_dashboard.html', today_appts=today_appointments,weekly_appts=weekly_appointments, patients=patients, status_labels=status_labels, status_values=status_values)

# Doctor appointments listed by day and week
@doctor_bp.route('/appointments')
@login_required
@role_required('doctor')
def appointments():
    doctor=_require_doctor_and_get()
    view_range=request.args.get('range','today')
    today=date.today()
    if view_range=='week':
        start=today-timedelta(days=today.weekday())
        end=start+timedelta(days=6)
        q=Appointment.query.filter_by(doctor_id=doctor.id).filter(Appointment.appt_date.between(start,end))
    else:
        q=Appointment.query.filter_by(doctor_id=doctor.id).filter(Appointment.appt_date==today)
    appts=q.order_by(Appointment.appt_date.asc(), Appointment.appt_time.asc()).all()
    filter_form=ApptFilterForm()
    status_form=ApptStatusForm()
    return render_template('doctor_appointments.html', appts=appts, filter_form=filter_form, status_form=status_form,view_range=view_range)    

# Set appointment status
@doctor_bp.route('/appointments/<int:appt_id>/status', methods=['POST'])
@login_required
@role_required('doctor')
def appointment_set_status_doctor(appt_id):
    doctor=_require_doctor_and_get()
    appt=Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doctor.id:
        abort(403)
    new_status= request.form.get('status')
    if new_status not in {'Booked','Completed','Cancelled'}:
        flash(f'Invalid status submission','danger')
        return redirect(url_for('doctor.appointments', range=request.args.get('range','today')))
    appt.status=new_status
    db.session.commit()
    flash(f'Appointment {appt.id} status updated to {new_status}','success')
    return redirect(url_for('doctor.appointments',range=request.args.get('range', 'today')))

# Doctor appointment treatment (Add/ Edit tratment)
@doctor_bp.route('/appointments/<int:appt_id>/treatment', methods=['GET','POST'])
@login_required
@role_required('doctor')
def appointment_treatment(appt_id):
    doctor=_require_doctor_and_get()
    appt=Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doctor.id:
        abort(403)
    form=TreatmentForm()
    if request.method=='GET':
        if appt.treatment:
            form.diagnosis.data=appt.treatment.diagnosis
            form.prescription.data=appt.treatment.prescription
            form.notes.data=appt.treatment.notes
    if form.validate_on_submit():
        if appt.treatment:
            appt.treatment.diagnosis=form.diagnosis.data
            appt.treatment.prescription=form.prescription.data
            appt.treatment.notes=form.notes.data
        else:
            t=Treatment(appointment_id=appt.id,diagnosis=form.diagnosis.data,prescription=form.prescription.data,notes=form.notes.data)
            db.session.add(t)
        if appt.status=='Booked':
            appt.status='Completed'
        db.session.commit()
        flash(f'Treatment for appointment {appt.id} updated','success')
        return redirect(url_for('doctor.appointments'))
    return render_template('doctor_treatment_form.html',form=form,appt=appt)

# View full patient their history
@doctor_bp.route('/patient/<int:patient_id>/history')
@login_required
@role_required('doctor')
def patient_history(patient_id):
    doctor=_require_doctor_and_get()
    appts=Appointment.query.filter_by(patient_id=patient_id, doctor_id=doctor.id).order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc()).all()
    pat=Patient.query.get_or_404(patient_id)
    return render_template('doctor_patient_history.html',appts=appts,patient=pat)

# 7 days availability
@doctor_bp.route('/availability',methods=['GET','POST'])
@login_required
@role_required('doctor')
def availability():
    doctor=_require_doctor_and_get()
    form=AvailabilityForm()
    if form.validate_on_submit():
        if form.end_time.data <= form.start_time.data:
            flash('End time must be after start time','warning')
        else:
            overlap=DoctorAvailability.query.filter_by(doctor_id=doctor.id, avail_date=form.date.data).filter(DoctorAvailability.start_time <= form.end_time.data ,DoctorAvailability.end_time >= form.start_time.data).first()
            if overlap:
                flash('Availability slot overlaps with existing slot','warning')
            else:
                slot=DoctorAvailability(
                    doctor_id=doctor.id,
                    avail_date=form.date.data,
                    start_time=form.start_time.data,
                    end_time=form.end_time.data
                )
                try:
                    db.session.add(slot)
                    db.session.commit()
                    flash('Availability added','success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error adding availability','danger')
        return redirect(url_for('doctor.availability'))
    today=date.today()
    limit= today+timedelta(days=7)
    slots=DoctorAvailability.query.filter_by(doctor_id=doctor.id).filter(DoctorAvailability.avail_date.between(today,limit)).order_by(DoctorAvailability.avail_date.asc(), DoctorAvailability.start_time.asc()).all()
    return render_template('doctor_availability.html',form=form,slots=slots)

@doctor_bp.route('/availability/<int:slot_id>/delete',methods=['POST'])
@login_required
@role_required('doctor')
def availability_delete(slot_id):
    doctor=_require_doctor_and_get()
    slot=DoctorAvailability.query.get_or_404(slot_id)
    if slot.doctor_id != doctor.id:
        abort(403)
    try:
        db.session.delete(slot)
        db.session.commit()
        flash(f'Availability deleted','success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting availability','danger')
    return redirect(url_for('doctor.availability'))

@doctor_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if getattr(current_user, "role", None) != "doctor":
        abort(403)

    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if doctor is None:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("doctor.dashboard"))

    form = DoctorProfileForm()

    if form.validate_on_submit():
        
        new_email = form.email.data.strip()
        existing = User.query.filter_by(email=new_email).first()
        if existing and existing.id != current_user.id:
            form.email.errors.append("This email is already registered with another account.")
            return render_template("doctor_profile.html", form=form)
        current_user.name = form.name.data.strip()
        current_user.email = new_email
        
        if form.password.data:
            current_user.password_hash = generate_password_hash(form.password.data)
        spec = form.specialization.data.strip() if form.specialization.data else None
        doctor.specialization = spec

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("doctor.profile"))

   
    if request.method == "GET":
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.specialization.data = doctor.specialization or ""

    return render_template("doctor_profile.html", form=form)


# --------------------------------------------------------
# ------- Patient Blueprint -------
# --------------------------------------------------------
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

# Helpers
def _require_patient_and_get():
    if not current_user.is_authenticated or current_user.role != 'patient':
        abort(403)
    if not current_user.patient:
        abort(403)
    if current_user.patient.is_blacklisted:
        logout_user()
        flash("Your account is blacklisted. Contact admin.","danger")
        return redirect(url_for('auth.login'))
    return current_user.patient

def _return_if_redirect(obj):
    return hasattr(obj, 'status_code')

def _thirty_minutes_slots(start_time, end_time):
    slots=[]
    current=datetime.combine(date.today(), start_time)
    end_date=datetime.combine(date.today(), end_time)
    while current + timedelta(minutes=30) <= end_date:
        slots.append(current.time())
        current += timedelta(minutes=30)
    return slots

def _available_slots_for(doctor_id, target_date):
    # No same day booking
    if target_date <= date.today():
        return []
    # Find all available slot for that date
    window=DoctorAvailability.query.filter_by(doctor_id=doctor_id, avail_date=target_date).all()
    slots_set=set()
    
    for w in window:
        current_dt=datetime.combine(target_date, w.start_time)
        end_dt=datetime.combine(target_date, w.end_time)
        while current_dt + timedelta(minutes=30) <= end_dt:
            slots_set.add(current_dt.time())
            current_dt += timedelta(minutes=30)
    if not slots_set:
        return []
    occupied=set(t[0] for t in db.session.query(Appointment.appt_time).filter(Appointment.doctor_id==doctor_id, Appointment.appt_date==target_date, Appointment.status.in_(['Booked', 'Completed']),).all())
    available=[t for t in slots_set if t not in occupied]
    return sorted(available)

def _next_7_days(exclude_today=True):
    start=date.today() + timedelta(days=1 if exclude_today else 0)
    return [start + timedelta(days=i) for i in range(0,7 if exclude_today else 7)]

# Patient dashboard
@patient_bp.route('/dashboard')
@login_required
@role_required('patient')
def dashboard():
    pat=_require_patient_and_get()
    if _return_if_redirect(pat):
        return pat
    today=date.today()
    upcoming=Appointment.query.filter_by(patient_id=pat.id).filter(Appointment.appt_date>today).filter(Appointment.status=='Booked').order_by(Appointment.appt_date.asc(), Appointment.appt_time.asc()).limit(10).all()
    past=Appointment.query.filter_by(patient_id=pat.id).filter(Appointment.appt_date<=today).order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc()).limit(10).all()

    departments=Department.query.order_by(Department.name.asc()).all()
    doctors=db.session.query(Doctor).join(User,Doctor.user_id==User.id).filter(Doctor.is_blacklisted==False).order_by(User.name.asc()).all()

    days=_next_7_days(exclude_today=True)
    availability_summary={}
    for d in doctors:
        per_day=[]
        for dt in days:
            per_day.append(len(_available_slots_for(d.id, dt)))
        availability_summary[d.id]=per_day
    
    status_order=['Completed','Booked','Cancelled']
    rows=(db.session.query(User.name, Appointment.status, func.count(Appointment.id)).join(Doctor, Doctor.user_id==User.id).join(Appointment, Appointment.doctor_id==Doctor.id).filter(Appointment.patient_id==pat.id).group_by(User.name, Appointment.status).all())
    counts_map={}
    doctor_names_set=set()
    for name, status, count in rows:
        doctor_names_set.add(name)
        counts_map[(name, status)]=count
    doctor_labels=sorted(doctor_names_set)
    booked_counts=[]
    completed_counts=[]
    cancelled_counts=[]
    for name in doctor_labels:
        booked_counts.append(counts_map.get((name, 'Booked'), 0))
        completed_counts.append(counts_map.get((name, 'Completed'), 0))
        cancelled_counts.append(counts_map.get((name, 'Cancelled'), 0))


    return render_template('patient_dashboard.html', upcoming=upcoming, past=past, doctors=doctors, availability_summary=availability_summary, days=days, departments=departments, doctor_labels=doctor_labels, booked_counts=booked_counts, completed_counts=completed_counts, cancelled_counts=cancelled_counts)

# Patient search doctors
@patient_bp.route('/doctors')
@login_required
@role_required('patient')
def search_doctors():
    pat=_require_patient_and_get()
    if _return_if_redirect(pat):
        return pat
    form=SearchForm(q=request.args.get('q','').strip())
    q=form.q.data or ''
    query=db.session.query(Doctor).join(User, Doctor.user_id==User.id).filter(Doctor.is_blacklisted==False)
    if q:
        like_q=f'%{q}%'
        query=query.filter(or_(User.name.ilike(like_q), Doctor.specialization.ilike(like_q)))
    doctors=query.order_by(User.name.asc()).all()

    days=_next_7_days(exclude_today=True)
    availability_summary={}
    for d in doctors:
        per_day_count=[]
        for dt in days:
            per_day_count.append(len(_available_slots_for(d.id, dt)))
        availability_summary[d.id]=per_day_count
        
    return render_template('patient_doctors_search.html', form=form, doctors=doctors, availability_summary=availability_summary, days=days)

# Patient book appointment
@patient_bp.route('/doctors/book/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def book_appointment(doctor_id):
    pat = _require_patient_and_get()
    if _return_if_redirect(pat):
        return pat

    doc = Doctor.query.get_or_404(doctor_id)
    if doc.is_blacklisted:
        abort(404)

    form = AppointmentBookForm()
    days = _next_7_days(exclude_today=True)

    if request.method == 'POST':
        selected_date_str = request.form.get('date')
    else:
        selected_date_str = request.args.get('date')

    selected_date = None
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None

    available_times = []
    if selected_date:
        available_times = [dt.strftime('%H:%M') for dt in _available_slots_for(doc.id, selected_date)]

    if request.method == 'POST' and form.validate_on_submit():
       
        if not selected_date:
            flash("Please select a valid date.", "danger")
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))

        allowed_days = _next_7_days(exclude_today=True)
        if selected_date not in allowed_days:
            flash("Please choose a date within the next 7 days (no same-day booking).", "warning")
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))

        selected_time_str = request.form.get('time')
        if not selected_time_str:
            flash("Please choose a time slot.", "danger")
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id, date=selected_date.isoformat()))

        if selected_time_str not in set(available_times):
            flash("Selected time is not available for the chosen date. Please choose another time.", "danger")
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id, date=selected_date.isoformat()))

        selected_time_obj = datetime.strptime(selected_time_str, '%H:%M').time()

        # At most one future booked appt per doctor per patient ---
        existing_future = Appointment.query.filter(
            Appointment.patient_id == pat.id,
            Appointment.doctor_id == doc.id,
            Appointment.status == 'Booked',
            Appointment.appt_date >= date.today()
        ).first()
        if existing_future:
            flash("You already have a future booked appointment with this doctor.", "warning")
            return redirect(url_for('patient.appointments'))
        
        # -----Check for time conflict with other appointments-----
        time_conflict = Appointment.query.filter(
            Appointment.patient_id == pat.id,
            Appointment.status == 'Booked',
            Appointment.appt_date == selected_date,
            Appointment.appt_time == selected_time_obj
        ).first()
        if time_conflict:
            flash("You already have another appointment at this time.", "warning")
            return redirect(url_for('patient.appointments'))
        appt = Appointment(
            patient_id=pat.id,
            doctor_id=doc.id,
            appt_date=selected_date,
            appt_time=selected_time_obj,
            status='Booked'
        )

        try:
            db.session.add(appt)
            db.session.commit()
            flash("Appointment booked successfully", "success")
            return redirect(url_for('patient.dashboard'))
        except IntegrityError:
            db.session.rollback()
            flash("Selected slot is no longer available. Please choose another time.", "danger")
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id, date=selected_date.isoformat()))
        except Exception:
            db.session.rollback()
            flash("Failed to book appointment. Please try again.", "danger")
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id, date=selected_date.isoformat()))
    return render_template(
        'patient_book_appointment.html',
        doctor=doc,
        form=form,
        days=days,
        selected_date=selected_date,
        available_times=available_times,
        selected_time=None
    )


# Patient appointments
@patient_bp.route('/appointments')
@login_required
@role_required('patient')
def appointments():
    pat=_require_patient_and_get()
    if _return_if_redirect(pat):
        return pat
    today=date.today()
    upcoming=Appointment.query.filter_by(patient_id=pat.id).filter(Appointment.appt_date>today).order_by(Appointment.appt_date.asc(), Appointment.appt_time.asc()).all()
    past=Appointment.query.filter_by(patient_id=pat.id).filter(Appointment.appt_date<=today).order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc()).all()

    return render_template('patient_appointments.html', upcoming=upcoming, past=past)

# Patient Reschedule appointment
@patient_bp.route('/appointments/<int:appt_id>/reschedule', methods=['GET','POST'])
@login_required
@role_required('patient')
def reschedule(appt_id):
    pat=_require_patient_and_get()
    if _return_if_redirect(pat):
        return pat
    appt=Appointment.query.get_or_404(appt_id)
    if appt.patient_id != pat.id:
        abort(403)
    
    if appt.status !='Booked':
        flash("Only booked appointments can be rescheduled.","warning")
        return redirect(url_for('patient.appointments'))
    
    if appt.appt_date <= date.today():
        flash("Past or today's appointments cannot be rescheduled.","warning")
        return redirect(url_for('patient.appointments'))

    doc=appt.doctor
    if not doc or doc.is_blacklisted:
        flash("Doctor unavailable for rescheduling.","warning")
        return redirect(url_for('patient.appointments'))
    form=AppointmentRescheduleForm()
    days=_next_7_days(exclude_today=True)

    if request.method=='POST':
        selected_date_str=request.form.get('date')
    else:
        selected_date_str=request.args.get('date')
    
    selected_date=None
    if selected_date_str:
        try:
            selected_date=datetime.strptime(selected_date_str,'%Y-%m-%d').date()
        except ValueError:
            selected_date=None
    availablity_times=[]
    
    if selected_date:
        availablity_times=[dt.strftime('%H:%M') for dt in _available_slots_for(doc.id, selected_date)]
    
    if request.method=='POST' and form.validate_on_submit():
        if not selected_date:
            flash("Please select a valid date.","danger")
            return redirect(url_for('patient.reschedule', appt_id=appt.id))
        
        if selected_date not in days:
            flash("Please choose a date within the next 7 days (no same-day booking).","warning")
            return redirect(url_for('patient.reschedule', appt_id=appt.id, date=selected_date.isoformat()))
        
        selected_time_str=request.form.get('time')
        
        if not selected_time_str:
            flash("Please choose a time slot.","danger")
            return redirect(url_for('patient.reschedule', appt_id=appt.id, date=selected_date.isoformat()))
        if selected_time_str not in set(availablity_times):
            flash("Selected time is not available for the chosen date. Please choose another time.","danger")
            return redirect(url_for('patient.reschedule', appt_id=appt.id, date=selected_date.isoformat()))
        
        selected_time_obj=datetime.strptime(selected_time_str,'%H:%M').time()

        
        conflict=Appointment.query.filter(
            Appointment.patient_id==pat.id,
            Appointment.status=='Booked',
            Appointment.appt_date==selected_date,
            Appointment.appt_time==selected_time_obj,
            Appointment.id != appt.id
        ).first()
        if conflict:
            flash("You already have another appointment at this time.","warning")
            return redirect(url_for('patient.appointments'))

        appt.appt_date=selected_date
        appt.appt_time=selected_time_obj
        try:
            db.session.commit()
            flash("Appointment rescheduled successfully.","success")
            return redirect(url_for('patient.appointments'))
        except IntegrityError:
            db.session.rollback()
            flash("Selected slot is no longer available. Please choose another time.","danger")
            return redirect(url_for('patient.reschedule', appt_id=appt.id, date=selected_date.isoformat()))
        except Exception:
            db.session.rollback()
            flash("Failed to reschedule appointment. Please try again.","danger")
            return redirect(url_for('patient.reschedule', appt_id=appt.id, date=selected_date.isoformat()))
    return render_template('patient_reschedule.html', appt=appt, doctor=doc, form=form, days=days, selected_date=selected_date, availablity_times=availablity_times)

# Patient cancel appointment
@patient_bp.route('/appointments/cancel/<int:appt_id>', methods=['GET','POST'])
@login_required
@role_required('patient')
def cancel(appt_id):
    pat=_require_patient_and_get()
    if _return_if_redirect(pat):
        return pat
    appt=Appointment.query.get_or_404(appt_id)
    if appt.patient_id != pat.id:
        abort(403)
    today_date=date.today()
    if appt.status !='Booked':
        flash("Only booked appointments can be cancelled.","warning")
        return redirect(url_for('patient.appointments'))
    if appt.appt_date <= today_date:
        flash("Past or today's appointments cannot be cancelled.","warning")
        return redirect(url_for('patient.appointments'))
    
    if request.method == 'POST':
        appt.status='Cancelled'
        try:
            db.session.commit()
            flash("Appointment cancelled successfully.", "success")
            return redirect(url_for('patient.appointments'))
        except Exception:
            db.session.rollback()
            flash("Failed to cancel appointment. Please try again.", "danger")

    return render_template('patient_cancel_confirm.html', appt=appt)

# Patient history of completed appointments
@patient_bp.route('/history')
@login_required
@role_required('patient')
def history():
    pat=_require_patient_and_get()
    if _return_if_redirect(pat):
        return pat
    appts=Appointment.query.filter_by(patient_id=pat.id, status='Completed').order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc()).all()
    return render_template('patient_history.html', appts=appts)

# Patient profile view and edit
@patient_bp.route('/profile', methods=['GET','POST'])
@login_required
@role_required('patient')
def profile():
    pat=_require_patient_and_get()
    if _return_if_redirect(pat):
        return pat
    user=pat.user
   
    if request.method=='POST':
        form=PatientSelfForm()
        if form.validate_on_submit():
            user.name=form.name.data.strip()
            pat.phone=form.phone.data.strip() if form.phone.data else None
            pat.address=form.address.data.strip() if form.address.data else None
            pat.age=form.age.data
            pat.gender=form.gender.data.strip() if form.gender.data else None
            pat.medical_history=form.medical_history.data.strip() if form.medical_history.data else None
            
            db.session.commit()
            flash("Profile updated successfully","success")
            return redirect(url_for('patient.profile'))
    else:
        form=PatientSelfForm(
            name=user.name,
            phone=pat.phone or '',
            address=pat.address or '',
            age=pat.age,
            gender=pat.gender or '',
            medical_history=pat.medical_history or ''
        )
    return render_template('patient_profile.html', form=form)