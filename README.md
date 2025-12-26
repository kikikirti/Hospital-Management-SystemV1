# Hospital Management System (HMS)

A complete role-based hospital management platform built with Flask, designed to streamline patient appointments, doctor scheduling, treatment records, and administrative operations.

This project is part of the **IIT Madras – BS Degree (MAD-I Course)** and follows all required guidelines including programmatic DB creation, role-based access, clean templates, and structured CRUD operations.

---

## Problem Statement

Hospitals often face challenges in managing patient records, doctor schedules, appointments, and treatment history due to manual or fragmented systems.  
This Hospital Management System (HMS) provides a unified platform for Admins, Doctors, and Patients, enabling efficient management of appointments, availability, medical records, and operational workflows using Flask, SQLite, and Jinja templates.

---

## Features

### Admin Panel
- Full CRUD for:
  - Doctors  
  - Patients  
  - Departments  
- Manage all appointments:
  - Complete / Cancel / Reopen
  - Delete with confirmation modals
- Search doctors & patients
- Blacklist/unblacklist users
- Auto-generated statistics dashboard:
  - Total doctors, patients, appointments
  - Booked / Completed / Cancelled counts
  - Chart.js visual analytics

---

### Doctor Panel
- View Today’s and Weekly appointments
- Update appointment status
- Add diagnosis, prescription, and notes
- Provide availability slots (next 7 days)
- Delete availability
- View patient medical history
- Update profile (name, email, specialization, password)

---

### Patient Panel
- Register & login
- Search doctors (name, specialization)
- View doctor availability (next 7 days)
- Book appointment
- Reschedule appointment
- Cancel appointment
- View upcoming and past appointments
- Treatment history summary
- Update profile (phone with +91 validation, address, age, gender, medical history)

---

## Roles & Functionalities (As Required by MAD-I)

### Admin
- Add, update, delete doctor profiles  
- Manage patients and departments  
- Manage all appointments system-wide  
- Search doctors/patients  
- Blacklist/unblacklist users  
- View analytics dashboard  

### Doctor
- View daily & weekly appointments  
- Complete, cancel, or reopen appointments  
- Add diagnosis, prescription, and notes  
- Provide availability  
- View patient medical histories  
- Update profile  

### Patient
- Register/login  
- Search doctors  
- View availability  
- Book/reschedule/cancel appointments  
- View appointment history and medical records  
- Update personal profile  

---

## Tech Stack

| Technology | Used For |
|-----------|----------|
| Flask | Backend framework |
| Jinja2 | Templating |
| SQLite | Programmatically created DB |
| Bootstrap 5 | Responsive UI |
| Chart.js | Analytics/Graphs |
| WTForms | Form handling |
| Flask-Login | Authentication |

> **Note:**  
> The SQLite database is created programmatically using SQLAlchemy models.  
> No manual DB creation tools (like DB Browser) were used, as required in MAD-I.

---

## Setup

### 1. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate

```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
flask run
```
### 4. Access the Application in Browser
Open your web browser and go to `http://127.0.0.1:5000/` to access the application.
---

## Issues Faced & Resolutions

| Issue No. | Problem Faced | Cause | Resolution |
|----------|----------------|--------|------------|
| **1** | Doctor availability not showing | Date mismatches (`datetime` vs `date`) | Normalized date comparisons and parsing using `datetime.strptime(...).date()` |
| **2** | Reschedule page not showing slots | Incorrect availability merge logic | Corrected query: `Availability.query.filter_by(..., avail_date=selected_date)` |
| **3** | Doctor unable to update appointment status | Missing DB commit | Added `db.session.commit()` + flash confirmation |
| **4** | Search returned empty results | Missing User model join | Implemented query with `join(User).filter(User.name.ilike(...))` |
| **5** | Delete actions failing (modal) | Incorrect dynamic URL replacement | Standardized template: `actionTemplate.replace("0", id)` |
| **6** | Patient history missing treatment entries | Relationship not eager-loaded | Added `joinedload(Appointment.treatment)` in query |
| **7** | Charts not loading (Admin/Doctor) | Python list not JSON-safe for JS | Wrapped values in `{{ variable | tojson }}` |
| **8** | Blacklisted users could still log in | No blacklist verification in auth | Added login rule: block login if `user.is_blacklisted` |
| **9** | Empty tables looked broken | Missing fallback UI | Added `"No data found"` message blocks in templates |
| **10** | Duplicate bookings for same slot | No conflict check before saving | Added check to prevent booking if same doctor/date/time exists |

