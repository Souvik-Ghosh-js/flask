from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Student, Payment
from utils import check_and_send_reminders
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
        # Columns: Student Name | Oct | Nov | ... | Sep
        for _, row in df.iterrows():
            student_name = str(row["Student's Name"]).strip()  # adjust column name if needed
            if not student_name:
                continue

            student = Student.get_by_name(student_name)
            if not student:
                continue  # skip if student not found

            # Loop through month columns
            for month in df.columns[1:]:
                raw_value = str(row[month]).strip().lower() if pd.notna(row[month]) else ""

                # Business logic: blank/NIL = unpaid, only "paid" = paid
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
@routes_bp.route('/send_reminders')
def send_reminders():
    check_and_send_reminders(force=True)
    flash('Reminders sent successfully!', 'success')
    return redirect(url_for('routes.dashboard'))
