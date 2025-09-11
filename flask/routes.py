from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Student, Payment
from utils import check_and_send_reminders , send_whatsapp_announcement
from datetime import datetime
from flask import Response
import csv
# Blueprint setup
routes_bp = Blueprint("routes", __name__)

# ---------------- Dashboard ----------------
@routes_bp.route('/')
def dashboard():
    students = Student.get_all()
    payments = Payment.get_all()
    
    total_students = len(students)
    paid_count = sum(1 for p in payments if p['status'] == 'paid')
    unpaid_count = sum(1 for p in payments if p['status'] == 'unpaid')
    
    return render_template(
        'dashboard.html',
        students=students,
        payments=payments,
        total_students=total_students,
        paid_count=paid_count,
        unpaid_count=unpaid_count
    )



@routes_bp.route('/export/<string:table>')
def export_csv(table):
    def generate():
        data = []
        if table == "students":
            data = Student.get_all()
            header = ["ID", "Name", "Phone", "Email"]
            yield ",".join(header) + "\n"
            for s in data:
                yield f"{s['id']},{s['name']},{s['phone']},{s['email']}\n"

        elif table == "payments":
            data = Payment.get_all()
            header = ["ID", "Student", "Month", "Year", "Amount", "Status"]
            yield ",".join(header) + "\n"
            for p in data:
                yield f"{p['id']},{p['students']['name']},{p['month']},{p['year']},{p['amount']},{p['status']}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table}.csv"}
    )
# ---------------- Student Routes ----------------
@routes_bp.route('/students')
def students():
    students = Student.get_all()
    return render_template('students.html', students=students)


import pandas as pd
from flask import request, redirect, url_for, flash

@routes_bp.route('/upload_students_excel', methods=['POST'])
def upload_students_excel():
    file = request.files.get('excel_file')

    if not file:
        flash("No file uploaded", "error")
        return redirect(url_for('routes.students'))

    inserted_count = 0
    skipped_count = 0

    try:
        # Read Excel directly from memory
        if file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file, header=None)
        else:
            df = pd.read_csv(file, header=None)

        existing_phones = set(s.phone for s in Student.get_all())  # get all existing phones

        # Skip header row, assume first col = phone, second col = name
        for i, row in df.iterrows():
            if i == 0:
                continue

            phone = str(row[0]).strip() if pd.notna(row[0]) else ""
            name = str(row[1]).strip() if pd.notna(row[1]) else ""

            # Skip if either missing
            if not phone or not name:
                skipped_count += 1
                continue

            # Handle duplicate phone numbers
            original_phone = phone
            while phone in existing_phones:
                phone = f"91{original_phone}"

            try:
                Student.create(name, phone)
                existing_phones.add(phone)
                inserted_count += 1
            except Exception as e_row:
                # Skip problematic row without breaking
                skipped_count += 1
                print(f"Skipping row {i} due to error: {e_row}")

        flash(f"Students uploaded successfully! Inserted: {inserted_count}, Skipped: {skipped_count}", "success")

    except Exception as e:
        flash(f"Error processing file: {e}", "error")

    return redirect(url_for('routes.students'))



@routes_bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        
        Student.create(name, phone)
        flash('Student added successfully!', 'success')
        return redirect(url_for('routes.students'))
    
    return render_template('add_student.html')

@routes_bp.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.get_by_id(student_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        Student.update(student_id, name, phone, email)
        flash('Student updated successfully!', 'success')
        return redirect(url_for('routes.students'))
    
    return render_template('edit_student.html', student=student)

@routes_bp.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    Student.delete(student_id)
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('routes.students'))

# ---------------- Payment Routes ----------------
@routes_bp.route('/payments')
def payments():
    payments = Payment.get_all()
    students = Student.get_all()
    current_year = datetime.now().year
    return render_template('payments.html', 
                         payments=payments, 
                         students=students,
                         current_year=current_year)

@routes_bp.route('/add_payment', methods=['POST'])
def add_payment():
    student_id = request.form.get('student_id')
    month = request.form.get('month')
    year = request.form.get('year')
    status = request.form.get('status')
    
    Payment.create(student_id, month, year, status)
    flash('Payment added successfully!', 'success')
    return redirect(url_for('routes.payments'))


import pandas as pd
from flask import request, redirect, url_for, flash

@routes_bp.route('/upload_payments_excel', methods=['POST'])
def upload_payments_excel():
    if 'excel_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('routes.payments'))

    file = request.files['excel_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('routes.payments'))

    try:
        df = pd.read_excel(file)

        # Normalize headers
        df.columns = [str(c).strip() for c in df.columns]

        # Identify required columns
        number_col = next((c for c in df.columns if "number" in c.lower()), None)
        name_col = next((c for c in df.columns if "name" in c.lower()), None)

        if not name_col:
            raise ValueError("Could not find a 'Student Name' column")
        if not number_col:
            raise ValueError("Could not find a 'Student Number' column")

        # Define valid month names
        valid_months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]

        # Only take columns that are valid months
        month_cols = [c for c in df.columns if c.lower() in valid_months]

        for _, row in df.iterrows():
            student_number = str(row[number_col]).strip() if pd.notna(row[number_col]) else None
            student_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else None

            if not student_name:
                continue

            # You can fetch student either by number or name
            student = Student.get_by_name(student_name) or Student.get_by_number(student_number)
            if not student:
                continue

            for month in month_cols:
                raw_value = str(row[month]).strip().lower() if pd.notna(row[month]) else ""

                # Business logic
                status = "paid" if raw_value == "paid" else "unpaid"

                # Determine year
                month_lower = month.lower()
                if month_lower in ["october", "november", "december"]:
                    year = 2024
                else:
                    year = 2025

                # Check existing payment
                existing_payment = Payment.get_by_student_month_year(student["id"], month, year)
                if existing_payment:
                    Payment.update(existing_payment["id"], status)
                else:
                    Payment.create(student["id"], month, year, status)



        flash("Payments uploaded successfully!", "success")
    except Exception as e:
        print(f"Error processing file: {e}")
        flash(f"Error processing file: {str(e)}", "danger")

    return redirect(url_for("routes.payments"))

@routes_bp.route('/update_payment_status/<int:payment_id>', methods=['POST'])
def update_payment_status(payment_id):
    status = request.form.get('status')
    Payment.update(payment_id, status)
    print(f"Updated payment {payment_id} to status {status}")
    flash('Status Updated successfully!', 'success')
    return redirect(url_for('routes.payments'))

# ---------------- Reminders ----------------
@routes_bp.route('/send_reminders', methods=['GET', 'POST'])
def send_reminders():
    if request.method == 'POST':
        user_message = request.form.get("message", "")
        check_and_send_reminders(force=True, user_message=user_message)
        flash('Reminders sent successfully!', 'success')
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.dashboard'))

@routes_bp.route("/announcement", methods=["GET"])
def announcement():
    return render_template("announcement.html")

@routes_bp.route("/send_announcement", methods=["POST"])
def send_announcement():
    data = request.json
    students = data.get("data", [])
    message = data.get("message", "")
    
    results = []
    for student in students:
        phone = student.get("phone")
        try:
            sid = send_whatsapp_announcement(phone,  message)
            results.append({"phone": phone, "status": "sent", "sid": sid})
        except Exception as e:
            results.append({"phone": phone, "status": f"failed: {e}"})
    print(results)
    flash('Announcements sent successfully!', 'success')
    return jsonify({"success": True, "results": results})