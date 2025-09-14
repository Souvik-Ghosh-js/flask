from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Student, Payment , Course
from utils import check_and_send_reminders , send_whatsapp_announcement , check_and_send_reminders_batch , send_voice_reminder , send_whatsapp_reminder
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
    batches = Course.get_all()
    return render_template('students.html', students=students , batches=batches)


import pandas as pd
from flask import request, redirect, url_for, flash


@routes_bp.route('/add-batch', methods=['GET', 'POST'])
def add_batch():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        if not name:
            flash("Batch name is required!", "danger")
            return redirect(url_for('routes.add_batch'))

        Course.create(name=name, description=description)
        flash(f"Batch '{name}' created successfully!", "success")
        return redirect(url_for('routes.add_batch'))

    # Get all batches with student counts
    batches = Course.get_all()
    return render_template('add_batch.html', batches=batches)


@routes_bp.route('/upload_students_excel', methods=['POST'])
def upload_students_excel():
    file = request.files.get('excel_file')
    batch_name = request.form.get('batch')  # <-- NEW

    if not batch_name:
        flash("Please select a batch before uploading.", "error")
        return redirect(url_for('routes.students'))

    if not file:
        flash("No file uploaded", "error")
        return redirect(url_for('routes.students'))

    inserted_count = 0
    skipped_count = 0

    try:
        # Read Excel or CSV directly from memory
        if file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file, header=None)
        else:
            df = pd.read_csv(file, header=None)

        existing_phones = set(s['phone'] for s in Student.get_all())

        # Skip header row, assume first col = phone, second col = name
        for i, row in df.iterrows():
            if i == 0:
                continue

            phone = str(row[0]).strip() if pd.notna(row[0]) else ""
            name = str(row[1]).strip() if pd.notna(row[1]) else ""

            # Skip if missing
            if not phone or not name:
                skipped_count += 1
                continue

            # Handle duplicate phone numbers
            original_phone = phone
            while phone in existing_phones:
                phone = f"91{original_phone}"

            try:
                Student.create(name=name, phone=phone, course=batch_name)  # <-- Pass batch
                existing_phones.add(phone)
                inserted_count += 1
            except Exception as e_row:
                skipped_count += 1
                print(f"Skipping row {i} due to error: {e_row}")

        flash(f"Students uploaded successfully to batch '{batch_name}'! "
              f"Inserted: {inserted_count}, Skipped: {skipped_count}", "success")

    except Exception as e:
        print(f"Error processing file: {e}")
        flash(f"Error processing file: {e}", "error")

    return redirect(url_for('routes.students'))


@routes_bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    # Use a proper Batch model method if you have one, otherwise call supabase here
    batches = Course.get_all()  # ✅ Cleaner than calling supabase directly

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        batch_name = request.form.get('batch')

        if not batch_name:
            flash("Please select a batch.", "error")
            return redirect(url_for('routes.add_student'))

        try:
            Student.create(name=name, phone=phone, course=batch_name)
            flash(f'Student added successfully to batch {batch_name}!', 'success')
        except Exception as e:
            flash(f"Error adding student: {e}", "error")

        return redirect(url_for('routes.students'))
    
    return render_template('add_student.html', batches=batches)

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
        # Detect file type by extension
        filename = file.filename.lower()
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        elif filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            flash("Unsupported file format. Please upload Excel (.xlsx, .xls) or CSV.", "danger")
            return redirect(url_for('routes.payments'))

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
    # ✅ Use model layer instead of supabase directly
    courses = Course.get_all()
    return render_template("announcement.html", batches=courses)


@routes_bp.route("/send_announcement", methods=["POST"])
def send_announcement():
    data = request.json
    students = data.get("data", [])
    batch_name = data.get("batch", None)
    message = data.get("message", "")

    results = []

    # ✅ Fetch students from model if batch is selected
    if batch_name:
        all_students = Student.get_all()
        students = [s for s in all_students if s.get("course") == batch_name]

    for student in students:
        phone = student.get("phone")
        try:
            sid = send_whatsapp_announcement(phone, message)
            results.append({"phone": phone, "status": "sent", "sid": sid})
        except Exception as e:
            results.append({"phone": phone, "status": f"failed: {e}"})

    flash('Announcements sent successfully!', 'success')
    return jsonify({"success": True, "results": results})




@routes_bp.route('/dues')
def dues():
    students = Student.get_all()
    payments = Payment.get_all()
    batches = Course.get_all()
    return render_template('dues.html', students=students, payments=payments, batches=batches)

@routes_bp.route('/export_dues')
def export_dues():
    batch = request.args.get('batch', '')
    month = request.args.get('month', '')
    
    def generate():
        header = ["Student Name", "Phone", "Batch", "Dues"]
        yield ",".join(header) + "\n"
        
        students = Student.get_all()
        payments = Payment.get_all()
        
        for student in students:
            dues = []
            for payment in payments:
                if payment['student_id'] == student['id'] and payment['status'] == 'unpaid':
                    if (not month or payment['month'].lower() == month.lower()) and \
                       (not batch or student['course'] == batch):
                        dues.append(f"{payment['month']} {payment['year']}")
            if dues:
                yield f"{student['name']},{student['phone']},{student['course']},\"{','.join(dues)}\"\n"
    
    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=dues.csv"}
    )



@routes_bp.route('/delete_batch/<int:course_id>', methods=['POST'])
def delete_batch(course_id):
    """
    Deletes a course (batch) and all students + payments inside that course.
    """
    result = Course.delete_with_students(course_id)

    if result.get("error"):
        flash(f"Error: {result['error']}", "danger")
    else:
        flash(f"Batch deleted successfully. {result['deleted_students']} students removed.", "success")
    
    return redirect(url_for('routes.add_batch'))  #


@routes_bp.route('/send_reminders_batch', methods=['POST'])
def send_reminders_batch():
    data = request.json
    batch = data.get('batch', '')
    month = data.get('month', '')
    user_message = data.get('message', '')

    # Get current date and time (fixed to September 13, 2025, 10:27 PM IST)

    if not user_message:
        flash('Please provide a reminder message.', 'danger')
        return jsonify({'success': False, 'message': 'No message provided'})

    # Call check_and_send_reminders with current time
    results = check_and_send_reminders_batch(
        user_message=user_message,
        batch=batch,
        month=month
    )

    if not results:
        flash('No students with dues found for the selected filters.', 'warning')
        return jsonify({'success': False, 'message': 'No students with dues found'})

    success = any(r['status'] == 'sent' for r in results)
    if success:
        flash('Reminders sent successfully!', 'success')
    else:
        flash('Some reminders failed to send.', 'warning')

    return jsonify({'success': success, 'results': results})


@routes_bp.route('/send_reminder_single', methods=['POST'])
def send_reminder_single():
    data = request.json
    phone = data.get("phone")
    name = data.get("name")
    months = data.get("months", [])
    message = data.get("message", "")

    if not phone or not name or not months:
        return jsonify({"success": False, "message": "Missing phone, name, or months"}), 400

    try:
        # Prepare month list string
        months_str = ", ".join(months)

        # Send WhatsApp reminder
        sid_whatsapp = send_whatsapp_reminder(phone, name, months_str, custom_message=message)

        # Send voice call reminder
        sid_voice = send_voice_reminder(phone, name, months_str)

        if sid_whatsapp or sid_voice:
            return jsonify({
                "success": True,
                "message": f"Reminder sent to {name} for {months_str}!",
                "whatsapp_sid": sid_whatsapp,
                "voice_sid": sid_voice
            })
        else:
            return jsonify({"success": False, "message": f"Failed to send reminders to {name}."}), 500

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
