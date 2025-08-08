from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Doctor, Clinic, SpecialityEnum
import bcrypt
import os
from datetime import datetime
from flask_mail import Mail, Message


def emailcorrecting(email):
    return email.strip().lower()

def get_time(booking):
    return f"{booking['date']} {booking['time']}"



app = Flask(__name__)
app.secret_key = os.urandom(24)


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ecoibookingsolutions@gmail.com'
app.config['MAIL_PASSWORD'] = 'abco kxob bvmz dmqy'
app.config['MAIL_DEFAULT_SENDER'] = ('Doctor Appointments', 'ecoibookingsolutions@gmail.com')

mail = Mail(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///doc_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

SPECIALTIES_FOR_TEMPLATE = [(member.name, member.value) for member in SpecialityEnum]


with app.app_context():
    db.create_all()
    if Clinic.query.count() == 0:
        default_clinics = [
            Clinic(name="Ruby Hall Clinic", location="Wanowrie"),
            Clinic(name="Medipoint Hospital", location="Aundh"),
            Clinic(name="Deenanath Mangeshkar Hospital", location="Erandwane"),
            Clinic(name="Lifeline Hospital", location="Baner")
        ]
        db.session.add_all(default_clinics)
        db.session.commit()



@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    clinics = Clinic.query.all()

    if request.method == 'POST':
        email = request.form['username']
        actual_email = emailcorrecting(request.form['actual_email'])
        password = request.form['password'].encode('utf-8')
        role = request.form.get('role')
        clinic_id = request.form.get('clinic_id')
        doc_code = request.form.get('doc_code', '').strip()

        if User.query.filter_by(email=email).first() or Doctor.query.filter_by(email=email).first():
            flash("Email already registered under another role.")
            return redirect('/register')

        
        if role == 'patient' and doc_code:
            flash("Patients should not enter a doctor code.")
            return redirect('/register')

        if role == 'doctor' and doc_code != 'doc123':
            flash("Invalid doctor code.")
            return redirect('/register')

        hashed = bcrypt.hashpw(password, bcrypt.gensalt())

        if role == 'doctor':
            speciality_name = request.form.get('speciality', '').strip()
            if not speciality_name:
                flash("Please select a speciality.")
                return render_template('register.html', clinics=clinics, specialties=SPECIALTIES_FOR_TEMPLATE)

            try:
                speciality_enum = SpecialityEnum[speciality_name]
            except KeyError:
                flash("Invalid speciality selected.")
                return render_template('register.html', clinics=clinics, specialties=SPECIALTIES_FOR_TEMPLATE)

            clinic = Clinic.query.get(int(clinic_id)) if clinic_id else None
            new_user = Doctor(
                email=email,
                password=hashed,
                speciality=speciality_enum,
                clinic=clinic,
                all_time=['10', '11', '12', '14', '15', '16', '17', '18', '19', '20', '21', '22'],
                booked_time=[],
                actual_email=actual_email
            )
        else:
            new_user = User(email=email, password=hashed, actual_email=actual_email)

        db.session.add(new_user)
        db.session.commit()
        flash("Registered successfully!")

        if role == 'doctor':
            return redirect('/login')
        else:
            session['user_id'] = new_user.id
            session['role'] = 'patient'
            return redirect('/login')

    return render_template('register.html', clinics=clinics, specialties=SPECIALTIES_FOR_TEMPLATE)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password'].encode('utf-8')
        doctor = Doctor.query.filter_by(email=email).first()
        user = User.query.filter_by(email=email).first()

        if doctor and bcrypt.checkpw(password, doctor.password):
            session['user_id'] = doctor.id
            session['role'] = 'doctor'
            flash("Login successful as Doctor!")
            return redirect('/doc_dashboard')

        elif user and bcrypt.checkpw(password, user.password):
            session['user_id'] = user.id
            session['role'] = 'patient'
            flash("Login successful as Patient!")
            return redirect('/select_clinic')

        else:
            flash("Invalid credentials.")
            return redirect('/login')

    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Unauthorized access.")
        return redirect('/login')

    clinic_id = request.args.get('clinic_id')
    speciality_name = request.args.get('speciality', '').strip()
    doc_id = request.args.get('doc_id')
    selected_date = request.args.get('selected_date')

    # Base doctor query
    query = Doctor.query
    if clinic_id:
        query = query.filter_by(clinic_id=int(clinic_id))
    if speciality_name:
        try:
            speciality_enum = SpecialityEnum[speciality_name]
            query = query.filter(Doctor.speciality == speciality_enum)
        except KeyError:
            flash("Invalid speciality filter.")

    docs = query.all()
    selected_doctor = Doctor.query.get(int(doc_id)) if doc_id else None

    if request.method == 'POST':
        form = request.form

        
        if 'time' in form and 'selected_doc_id' in form and 'selected_date' in form:
            time = form.get('time')
            date = form.get('selected_date')
            doc_id = form.get('selected_doc_id')
            patient = User.query.get(session['user_id'])

            if not doc_id or not time or not date:
                flash("Incomplete booking details.")
                return redirect(url_for('dashboard', clinic_id=clinic_id, speciality=speciality_name))

            doctor = Doctor.query.get(int(doc_id))
            if not doctor:
                flash("Doctor not found.")
                return redirect(url_for('dashboard', clinic_id=clinic_id, speciality=speciality_name))

            booked = doctor.booked_time or []
            if any(slot['time'] == time and slot['date'] == date for slot in booked):
                flash("This time slot on selected date is already booked.")
                return redirect(url_for('dashboard', clinic_id=clinic_id, speciality=speciality_name, doc_id=doc_id, selected_date=date))

           
            booked.append({"time": time, "date": date, "patient_email": patient.email})
            doctor.booked_time = booked
            db.session.commit()

        
            msg_doc = Message(
                subject="New Appointment Booking",
    recipients=[doctor.actual_email],
    body=(
        f"Respected Dr. {doctor.email},\n\n"
        f"You have received a booking from patient {patient.email} at {time}:00.\n\n"
        "Thanks and Regards\n"
        "ECOI Solutions"
            )
            )
            mail.send(msg_doc)

            
            msg_patient = Message(
                subject="Appointment Confirmation",
    recipients=[patient.actual_email],
    body=(
        f"Respected {patient.email},\n\n"
        f"Your booking has been confirmed from {time}:00  with Dr. {doctor.email}.\n\n"
        "Thanks and Regards\n"
        "ECOI Solutions"
            )
            )
            mail.send(msg_patient)

            flash("Booking successful and confirmation emails sent!")
            return redirect(url_for('dashboard',doc_id=doctor.id, selected_date=date))
            

        
        elif 'doc_id' in form:
            doc_id = form.get('doc_id')
            return redirect(url_for('dashboard', clinic_id=clinic_id, speciality=speciality_name, doc_id=doc_id))

    
        elif 'selected_date' in form and 'selected_doc_id' in form:
            date = form.get('selected_date')
            doc_id = form.get('selected_doc_id')
            return redirect(url_for('dashboard', clinic_id=clinic_id, speciality=speciality_name, doc_id=doc_id, selected_date=date))

        flash("Invalid form submission.")
        return redirect(url_for('dashboard', clinic_id=clinic_id, speciality=speciality_name))

    
    booked_slot_times = []
    if selected_doctor and selected_date:
        booked_slot_times = [
            (selected_doctor.id, slot['time'])
            for slot in (selected_doctor.booked_time or [])
            if slot['date'] == selected_date
        ]

    return render_template(
        'dashboard.html',
        docs=docs,
        selected_doctor=selected_doctor,
        selected_date=selected_date,
        booked_slot_times=booked_slot_times
    )


@app.route('/select_clinic')
def select_clinic():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Unauthorized access.")
        return redirect('/login')

    clinics = Clinic.query.all()
    return render_template('clinic_selection.html', clinics=clinics, specialties=SPECIALTIES_FOR_TEMPLATE)


@app.route('/doc_dashboard')
def doc_dashboard():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Unauthorized access.")
        return redirect('/login')

    doctor = Doctor.query.get(session['user_id'])
    bookings = doctor.booked_time or []

    
    calendar_events = [
        {
            "title": f"{slot['patient_email']} - {slot['time']}:00",
            "start": f"{slot['date']}T{slot['time']}:00"
        }
        for slot in bookings
    ]

    bookings.sort(key=get_time)
    return render_template('doc_dashboard.html', bookings=bookings, doctor=doctor, events=calendar_events)


@app.route('/clinic_select', methods=['POST'])
def go_to_doctor_page():
    clinic_id = request.form.get('clinic_id', '').strip()
    speciality = request.form.get('speciality', '').strip()

    if not clinic_id:
        flash("Please choose a clinic.")
        return redirect(url_for('select_clinic'))

    if speciality:
        try:
            _ = SpecialityEnum[speciality]
        except KeyError:
            flash("Invalid speciality selected.")
            return redirect(url_for('select_clinic'))

    return redirect(url_for('dashboard', clinic_id=clinic_id, speciality=speciality))


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect('/login')


@app.route('/appointments')
def appointments():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Unauthorized access.")
        return redirect('/login')

    doctor = Doctor.query.get(session['user_id'])
    bookings = doctor.booked_time if doctor else []

    return render_template('appointments.html', bookings=bookings, doctor=doctor)

@app.route('/review')
def review():
    return render_template('review.html')

if __name__ == '__main__':
    app.run(debug=True)
