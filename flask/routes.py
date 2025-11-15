from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Student, Payment, Course
from utils import check_and_send_reminders, send_whatsapp_announcement, check_and_send_reminders_batch, send_voice_reminder, send_whatsapp_reminder
from datetime import datetime
from flask import Response
import csv
import pandas as pd
import chardet
from io import BytesIO

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
            header = ["ID", "Name", "Phone", "Email", "Batch"]
            yield ",".join(header) + "\n"
            for s in data:
                yield f"{s['id']},{s['name']},{s['phone']},{s.get('email', '')},{s.get('course', '')}\n"

        elif table == "payments":
            data = Payment.get_all()
            header = ["ID", "Student", "Phone", "Batch", "Month", "Year", "Amount", "Status"]
            yield ",".join(header) + "\n"
            for p in data:
                yield f"{p['id']},{p['students']['name']},{p['students']['phone']},{p['students'].get('course', '')},{p['month']},{p['year']},{p.get('amount', '')},{p['status']}\n"

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
    return render_template('students.html', students=students, batches=batches)

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

    batches = Course.get_all()
    return render_template('add_batch.html', batches=batches)

@routes_bp.route('/upload_students_excel', methods=['POST'])
def upload_students_excel():
    file = request.files.get('excel_file')
    batch_name = request.form.get('batch')

    if not batch_name:
        flash("Please select a batch before uploading.", "error")
        return redirect(url_for('routes.students'))

    if not file:
        flash("No file uploaded", "error")
        return redirect(url_for('routes.students'))

    try:
        # Read file
        if file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file, header=None)
        else:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            detected_encoding = result.get("encoding", "utf-8")
            try:
                df = pd.read_csv(BytesIO(raw_data), header=None, encoding=detected_encoding)
            except UnicodeDecodeError:
                df = pd.read_csv(BytesIO(raw_data), header=None, encoding="latin1")

        print(f"Processing {len(df)} rows from uploaded file")

        # Get existing students in this batch for duplicate checking
        print("Fetching existing students in batch...")
        all_students = Student.get_all()
        existing_students_dict = {
            student['phone']: student for student in all_students 
            if student.get('course') == batch_name
        }
        existing_phones = set(existing_students_dict.keys())
        print(f"Found {len(existing_phones)} existing students in batch '{batch_name}'")

        # Collect valid student data
        print("Processing rows...")
        students_to_insert = []
        duplicate_count = 0
        invalid_count = 0
        
        for i, row in df.iterrows():
            if i == 0:  # Skip header row
                continue

            phone = str(row[0]).strip() if pd.notna(row[0]) else ""
            name = str(row[1]).strip() if pd.notna(row[1]) else ""

            # Validate required fields
            if not phone or not name:
                invalid_count += 1
                continue

            # Check for duplicates in batch
            if phone in existing_phones:
                duplicate_count += 1
                continue

            students_to_insert.append({
                'name': name,
                'phone': phone,
                'course': batch_name
            })
            existing_phones.add(phone)  # Prevent duplicates in same upload

        print(f"Prepared {len(students_to_insert)} students for bulk insertion")

        # Bulk insert using the new method
        if students_to_insert:
            inserted_count = Student.bulk_create(students_to_insert)
            flash(
                f"Bulk upload successful! "
                f"Inserted: {inserted_count} students into batch '{batch_name}'. "
                f"Duplicates skipped: {duplicate_count}, "
                f"Invalid rows: {invalid_count}",
                "success"
            )
        else:
            flash(
                f"No new students to add. "
                f"Duplicates: {duplicate_count}, Invalid rows: {invalid_count}",
                "warning"
            )

    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error processing file: {str(e)}", "error")

    return redirect(url_for('routes.students'))

@routes_bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    batches = Course.get_all()

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        batch_name = request.form.get('batch')

        if not batch_name:
            flash("Please select a batch.", "error")
            return redirect(url_for('routes.add_student'))

        try:
            # Check if student already exists in this batch
            existing_student = Student.get_by_phone_and_batch(phone, batch_name)
            if existing_student:
                flash(f"Student with phone {phone} already exists in batch {batch_name}!", "error")
                return redirect(url_for('routes.add_student'))
            
            Student.create(name=name, phone=phone, course=batch_name)
            flash(f'Student added successfully to batch {batch_name}!', 'success')
        except Exception as e:
            flash(f"Error adding student: {e}", "error")

        return redirect(url_for('routes.students'))
    
    return render_template('add_student.html', batches=batches)

@routes_bp.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.get_by_id(student_id)
    batches = Course.get_all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        batch = request.form.get('batch')
        
        try:
            # Check if another student with same phone exists in the target batch
            if phone != student['phone'] or batch != student['course']:
                existing_student = Student.get_by_phone_and_batch(phone, batch)
                if existing_student and existing_student['id'] != student_id:
                    flash(f"Another student with phone {phone} already exists in batch {batch}!", "error")
                    return redirect(url_for('routes.edit_student', student_id=student_id))
            
            Student.update(student_id, name=name, phone=phone, email=email, course=batch)
            flash('Student updated successfully!', 'success')
        except Exception as e:
            flash(f"Error updating student: {e}", "error")
        
        return redirect(url_for('routes.students'))
    
    return render_template('edit_student.html', student=student, batches=batches)


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
    batches = Course.get_all()
    current_year = datetime.now().year
    return render_template('payments.html', 
                         payments=payments, 
                         students=students,
                         batches=batches,
                         current_year=current_year)

@routes_bp.route('/add_payment', methods=['POST'])
def add_payment():
    student_id = request.form.get('student_id')
    month = request.form.get('month')
    year = request.form.get('year')
    status = request.form.get('status')
    batch = request.form.get('batch')  # Get batch from form
    
    try:
        # Validate that the student belongs to the selected batch
        student = Student.get_by_id(student_id)
        if not student:
            flash('Student not found!', 'danger')
            return redirect(url_for('routes.payments'))
        
        if student.get('course') != batch:
            flash(f'Error: Student does not belong to batch "{batch}"!', 'danger')
            return redirect(url_for('routes.payments'))
        
        Payment.create(student_id, month, year, status, batch)
        flash('Payment added successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('routes.payments'))

@routes_bp.route('/upload_payments_excel', methods=['POST'])
def upload_payments_excel():
    print("=== BULK UPLOAD WITH DEDUPLICATION ===")
    
    if 'excel_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('routes.payments'))

    file = request.files['excel_file']
    selected_batch = request.form.get('batch')

    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('routes.payments'))

    if not selected_batch:
        flash('Please select a batch before uploading.', 'danger')
        return redirect(url_for('routes.payments'))

    try:
        # Read file
        filename = file.filename.lower()
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            detected_encoding = result.get("encoding", "utf-8")
            df = pd.read_csv(BytesIO(raw_data), encoding=detected_encoding)

        print(f"File loaded: {df.shape[0]} rows, {df.shape[1]} columns")

        # Normalize headers
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identify columns
        number_col = next((c for c in df.columns if "number" in c.lower() or "phone" in c.lower()), None)
        name_col = next((c for c in df.columns if "name" in c.lower()), None)

        if not name_col:
            raise ValueError("Could not find a 'Student Name' column")

        valid_months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]

        month_cols = [c for c in df.columns if c.lower() in valid_months]
        print(f"Processing {len(month_cols)} months: {month_cols}")

        if not month_cols:
            flash("No valid month columns found in the file", "danger")
            return redirect(url_for('routes.payments'))

        # STEP 1: Load students
        print("Step 1: Loading students...")
        all_students = Student.get_all()
        batch_students = [s for s in all_students if s.get('course') == selected_batch]
        
        # Create fast lookup dictionaries
        student_by_phone = {s['phone']: s for s in batch_students}
        student_by_name_lower = {s['name'].strip().lower(): s for s in batch_students}
        
        print(f"Found {len(batch_students)} students in batch '{selected_batch}'")

        # STEP 2: Determine year assignment for each column (ONCE)
        print("Step 2: Determining year assignment for each month column...")
        
        # Pre-determine the year for each month column
        month_year_mapping = {}
        current_year = 2024
        
        for month in month_cols:
            month_lower = month.lower()
            
            # If we encounter January, switch to 2025 for this and all subsequent months
            if month_lower == "january" and current_year == 2024:
                current_year = 2025
                print(f"Encountered January, switching to year {current_year} for remaining months")
            
            month_year_mapping[month] = current_year
            print(f"Column '{month}' assigned to year {current_year}")

        # STEP 3: Collect payment data with deduplication
        print("Step 3: Collecting and deduplicating payment data...")
        
        payments_dict = {}  # Use dictionary to automatically handle duplicates
        paid_count = 0
        unpaid_count = 0
        duplicate_count = 0

        for index, row in df.iterrows():
            student_number = str(row[number_col]).strip() if pd.notna(row[number_col]) else ""
            student_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""

            if not student_name:
                continue

            # Find student
            student = None
            if student_number and student_number in student_by_phone:
                student = student_by_phone[student_number]
            elif student_name.lower() in student_by_name_lower:
                student = student_by_name_lower[student_name.lower()]

            if not student:
                print(f"Student not found: {student_name}")
                continue

            # Process each month using pre-determined year mapping
            for month in month_cols:
                raw_value = row[month]
                
                # Determine status
                if pd.isna(raw_value) or str(raw_value).strip().lower() != 'paid':
                    status = "unpaid"
                else:
                    status = "paid"

                # Get the pre-determined year for this column
                year = month_year_mapping[month]
                
                # Create unique key for this student-month-year
                unique_key = f"{student['id']}_{month}_{year}"
                
                # Only add if this combination doesn't exist (keep first occurrence)
                if unique_key not in payments_dict:
                    payments_dict[unique_key] = {
                        'student_id': student['id'],
                        'month': month,
                        'year': year,
                        'status': status
                    }
                    
                    # Count for statistics
                    if status == "paid":
                        paid_count += 1
                    else:
                        unpaid_count += 1
                else:
                    # This is a duplicate - skip it
                    duplicate_count += 1
                    print(f"Duplicate found: {unique_key} - keeping first occurrence")

        # Convert dictionary back to list
        payments_data = list(payments_dict.values())
        
        print(f"After deduplication: {len(payments_data)} unique payments (Removed {duplicate_count} duplicates)")
        print(f"Payment breakdown - Paid: {paid_count}, Unpaid: {unpaid_count}")

        # STEP 4: Execute bulk upsert on deduplicated data
        print("Step 4: Executing bulk upsert on deduplicated data...")
        
        if payments_data:
            processed_count = Payment.bulk_upsert(payments_data)
            print(f"Successfully processed {processed_count} payments")
            
            flash(f"Payments uploaded successfully! Processed {processed_count} unique payment records (Paid: {paid_count}, Unpaid: {unpaid_count}, Duplicates removed: {duplicate_count})", "success")
        else:
            flash("No payments to process from the file", "warning")

    except Exception as e:
        print(f"=== CRITICAL ERROR ===")
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        flash(f"Error processing file: {str(e)}", "danger")

    return redirect(url_for("routes.payments"))


@routes_bp.route('/update_payment_status/<int:payment_id>', methods=['POST'])
def update_payment_status(payment_id):
    status = request.form.get('status')
    Payment.update(payment_id, status)
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
    courses = Course.get_all()
    return render_template("announcement.html", batches=courses)

@routes_bp.route("/send_announcement", methods=["POST"])
def send_announcement():
    data = request.json
    students = data.get("data", [])
    batch_name = data.get("batch", None)
    message = data.get("message", "")

    results = []

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
                if (payment['student_id'] == student['id'] and 
                    payment['status'] == 'unpaid' and
                    payment['students'].get('course') == student.get('course')):
                    if (not month or payment['month'].lower() == month.lower()) and \
                       (not batch or student['course'] == batch):
                        dues.append(f"{payment['month']} {payment['year']}")
            if dues:
                yield f"{student['name']},{student['phone']},{student.get('course', '')},\"{','.join(dues)}\"\n"
    
    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=dues.csv"}
    )

@routes_bp.route('/delete_batch/<int:course_id>', methods=['POST'])
def delete_batch(course_id):
    result = Course.delete_with_students(course_id)

    if result.get("error"):
        flash(f"Error: {result['error']}", "danger")
    else:
        flash(f"Batch deleted successfully. {result['deleted_students']} students removed.", "success")
    
    return redirect(url_for('routes.add_batch'))

@routes_bp.route('/send_reminders_batch', methods=['POST'])
def send_reminders_batch():
    data = request.json
    batch_filter = data.get('batch', '')
    month_filter = data.get('month', '')
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({'success': False, 'message': 'Please provide a reminder message.'}), 400

    try:
        # Get all students and payments
        all_students = Student.get_all()
        all_payments = Payment.get_all()
        
        # Filter students based on batch
        if batch_filter:
            filtered_students = [s for s in all_students if s.get('course') == batch_filter]
        else:
            filtered_students = all_students
        
        results = []
        
        for student in filtered_students:
            # Get unpaid payments for this student
            unpaid_payments = []
            for payment in all_payments:
                if (payment['student_id'] == student['id'] and 
                    payment['status'] == 'unpaid' and
                    payment['students'].get('course') == student.get('course')):
                    
                    # Apply month filter if specified
                    if not month_filter or payment['month'].lower() == month_filter.lower():
                        unpaid_payments.append(f"{payment['month']} {payment['year']}")
            
            # If student has dues after filtering, send reminder
            if unpaid_payments:
                months_str = ", ".join(unpaid_payments)
                try:
                    # Send WhatsApp reminder
                    sid_whatsapp = send_whatsapp_reminder(
                        student['phone'], 
                        student['name'], 
                        months_str, 
                        custom_message=user_message
                    )
                    print(f"WhatsApp reminder sent to {student['name']} ({student['phone']}) for months: {months_str}")
                    # Send voice reminder
                    sid_voice = send_voice_reminder(
                        student['phone'], 
                        student['name'], 
                        months_str
                    )
                    
                    results.append({
                        'phone': student['phone'],
                        'name': student['name'],
                        'months': months_str,
                        'status': 'sent',
                        'whatsapp_sid': sid_whatsapp,
                        'voice_sid': sid_voice
                    })
                    
                except Exception as e:
                    results.append({
                        'phone': student['phone'],
                        'name': student['name'],
                        'months': months_str,
                        'status': f'failed: {str(e)}'
                    })

        if not results:
            return jsonify({
                'success': False, 
                'message': 'No students with dues found for the selected filters.'
            }), 404

        # Count successful sends
        successful_sends = sum(1 for r in results if r['status'] == 'sent')
        total_students = len(results)
        
        if successful_sends > 0:
            message = f'Reminders sent successfully! {successful_sends}/{total_students} students notified.'
            return jsonify({
                'success': True, 
                'message': message,
                'results': results
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'All reminders failed to send.',
                'results': results
            }), 500

    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error processing batch reminders: {str(e)}'
        }), 500
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
        months_str = ", ".join(months)
        sid_whatsapp = send_whatsapp_reminder(phone, name, months_str, custom_message=message)
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