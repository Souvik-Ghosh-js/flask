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

@routes_bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        Student.create(name, phone, email)
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
    amount = request.form.get('amount')
    status = request.form.get('status')
    
    Payment.create(student_id, month, year, amount, status)
    flash('Payment added successfully!', 'success')
    return redirect(url_for('routes.payments'))

@routes_bp.route('/update_payment_status/<int:payment_id>', methods=['POST'])
def update_payment_status(payment_id):
    status = request.form.get('status')
    Payment.update(payment_id, status)
    return jsonify({'success': True})

# ---------------- Reminders ----------------
@routes_bp.route('/send_reminders')
def send_reminders():
    check_and_send_reminders(force=False)
    flash('Reminders sent successfully!', 'success')
    return redirect(url_for('routes.dashboard'))
