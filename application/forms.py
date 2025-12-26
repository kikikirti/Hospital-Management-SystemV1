from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, Regexp

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired('Email is required'), Email('Enter a valid email address'), Length(max=250)],render_kw={"required": True, "autocomplete": "email"})
    password = PasswordField('Password', validators=[DataRequired('Password is required'), Length(min=6, max=50, message='Password must be between 6 and 50 characters')],render_kw={"required": True, "autocomplete": "current-password"})
    submit = SubmitField('Log In')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired('Name is required'), Length(min=2, max=120)],render_kw={"required": True})
    email = StringField('Email', validators=[DataRequired('Email is required'), Email('Enter a valid email address'), Length(max=250)],render_kw={"required": True})
    password = PasswordField('Password', validators=[DataRequired('Password is required'), Length(min=6, max=50, message='Password must be between 6 and 50 characters')],render_kw={"required": True})
    submit = SubmitField('Register')

class SearchForm(FlaskForm):
    q=StringField("Search",validators=[Optional(), Length(max=120)])

class DoctorForm(FlaskForm):
    name=StringField("Name", validators=[DataRequired('Name is required'), Length(min=2,max=120)],render_kw={"required": True})
    email=StringField("Email", validators=[DataRequired('Email is required'), Email(), Length(max=250)],render_kw={"required": True})
    password=PasswordField("Password", validators=[Optional(),Length(min=6,max=50,message='Password must be between 6 and 50 characters')])
    specialization=StringField("Specialization",validators=[Optional(),Length(max=120)])
    department=SelectField("Department",coerce=int,validators=[Optional()],render_kw={"class":"form-select"})
    submit=SubmitField("Save")

class PatientForm(FlaskForm):
    name=StringField("Name", validators=[DataRequired('Name is required'),Length(min=2,max=120)],render_kw={"required": True})
    email=StringField("Email",validators=[DataRequired('Email is required'),Email(),Length(max=250)],render_kw={"required": True})
    password=PasswordField("Password",validators=[DataRequired('Password is required'),Length(min=5,max=50)],render_kw={"required": True})
    phone=StringField("Phone",validators=[Optional(),Length(min=10,max=10,message="Phone number must be 10 digits long"),Regexp(r'^\d{10}$',message="Phone number must contain only digits."),])
    address=StringField("Address",validators=[Optional(),Length(max=255)])
    age=IntegerField("Age",validators=[Optional(), NumberRange(min=0,max=120, message='Age must be between 0 and 120')])
    gender=SelectField("Gender",choices=[('', 'Select Gender'),("Male",'Male'),('Female','Female'),('Other','Other')], validators=[Optional()])
    medical_history=StringField("Medical History",validators=[Optional(),Length(max=5000)])
    submit=SubmitField("Save")

class TreatmentForm(FlaskForm):
    diagnosis=TextAreaField('Diagnosis',validators=[Optional(), Length(max=5000)])
    prescription=TextAreaField('Prescription',validators=[Optional(), Length(max=5000)])
    notes=TextAreaField('Notes',validators=[Optional(), Length(max=5000)])
    submit=SubmitField("Save Treatment")

class AvailabilityForm(FlaskForm):
    date=DateField('Date', format='%Y-%m-%d',validators=[DataRequired('Date is required')],render_kw={"required": True})
    start_time=TimeField('Start Time', format='%H:%M',validators=[DataRequired('Start Time is required')],render_kw={"required": True})
    end_time=TimeField('End Time',format='%H:%M',validators=[DataRequired('End Time is required')],render_kw={"required": True})
    submit=SubmitField("Add Slot")
    
class ApptStatusForm(FlaskForm):
    status=SelectField('Status',choices=[('Booked','Booked'),('Completed','Completed'),('Cancelled','Cancelled')],validators=[DataRequired('Status is required')],render_kw={"required": True})
    submit=SubmitField("Update")

class ApptFilterForm(FlaskForm):
    view_range=SelectField('Range',choices=[('today','Today'),('week','Week'),('month','Month')],validators=[DataRequired('View Range is required')],default='today',render_kw={"required": True})
    submit=SubmitField("Apply Filter")

class PatientSelfForm(FlaskForm):
    name=StringField('Name',validators=[DataRequired('Name is required'), Length(min=2,max=120)],render_kw={"required": True})
    phone=StringField('Phone',validators=[DataRequired('Phone is required'), Length(min=10, max=10, message="Phone number must be 10 digits"), Regexp('^\d{10}$', message="Phone number must contain only digits"),],render_kw={"required": True})
    address=StringField('Address',validators=[DataRequired('Address is required'), Length(max=255)],render_kw={"required": True})
    age=IntegerField('Age',validators=[DataRequired('Age is required'), NumberRange(min=0,max=120,message='Age must be between 0 and 120')],render_kw={"required": True,"min":0,"max":120})
    gender=SelectField("Gender",choices=[('','Select Gender'),("Male","Male"),('Female','Female'),('Other','Other')], validators=[Optional()])
    medical_history=StringField('Medical History',validators=[Optional(), Length(max=5000)])
    submit=SubmitField("Save")

class AppointmentBookForm(FlaskForm):
    submit=SubmitField("Book Appointment")

class AppointmentRescheduleForm(FlaskForm):
    date=DateField('New Date',format='%Y-%m-%d',validators=[DataRequired('Date is required')],render_kw={"required": True})
    time=TimeField('New Time',format='%H:%M',validators=[DataRequired('Time is required')],render_kw={"required": True})
    submit=SubmitField("Reschedule Appointment")

class DepartmentForm(FlaskForm):
    name=StringField('Name',validators=[DataRequired('Department name is required'), Length(min=5, max=100)],render_kw={"required": True})
    description=StringField('Description',validators=[Optional(), Length(max=5000)])
    submit=SubmitField("Save Department")

class DoctorCreateForm(DoctorForm):
    """Used for create doctor- password required."""
    password=PasswordField('Password', validators=[DataRequired('Password is required'), Length(min=5, max=50,message='Password must be between 5 and 50 characters long')],render_kw={"required": True})

class DoctorProfileForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired(message="Name is required."),Length(min=2, max=80, message="Name must be between 2 and 80 characters."),],)
    email = StringField("Email",validators=[DataRequired(message="Email is required."), Email(message="Enter a valid email address."),Length(max=120, message="Email must be at most 120 characters."),],)
    password = PasswordField("New Password",validators=[Optional(),Length(min=6, max=128, message="Password must be between 6 and 128 characters."),],)
    specialization = StringField("Specialization",validators=[Length(max=120, message="Specialization must be at most 120 characters."),],)
    submit = SubmitField("Save Changes")