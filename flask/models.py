from supabase import create_client, Client
import os
from config import Config

supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

class Student:
    @staticmethod
    def get_all():
        response = supabase.table('students').select('*, course').execute()
        return response.data

    @staticmethod
    def get_by_name(name):
        response = supabase.table('students').select('*, course').eq('name', name).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_by_id(student_id):
        response = supabase.table('students').select('*, course').eq('id', student_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def create(name, phone, course=None):
        """
        Creates a student.
        - `course` can represent the batch name.
        """
        data = {
            'name': name,
            'phone': phone,
            'course': course
        }
        # Remove None fields
        data = {k: v for k, v in data.items() if v is not None}

        response = supabase.table('students').insert(data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def update(student_id, name=None, phone=None, email=None, course=None):
        """
        Updates a student record. Only updates fields that are passed.
        """
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if phone is not None:
            update_data['phone'] = phone
        if email is not None:
            update_data['email'] = email
        if course is not None:
            update_data['course'] = course

        if not update_data:
            return None

        response = supabase.table('students').update(update_data).eq('id', student_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def delete(student_id):
        response = supabase.table('students').delete().eq('id', student_id).execute()
        return response.data


class Course:
    @staticmethod
    def get_all():
        # 1. Get all courses
        courses_response = supabase.table('courses').select('*').execute()
        courses = courses_response.data or []

        # 2. Get all students
        students_response = supabase.table('students').select('id, name, course').execute()
        students = students_response.data or []

        # 3. Get all payments
        payments_response = supabase.table('payments').select('student_id, status').execute()
        payments = payments_response.data or []

        # Build a map of student_id -> payment status list
        student_payments = {}
        for p in payments:
            sid = p["student_id"]
            if sid not in student_payments:
                student_payments[sid] = []
            student_payments[sid].append(p["status"])

        # Build stats per course
        course_stats = {}
        for student in students:
            course_name = student.get("course")
            if not course_name:
                continue

            if course_name not in course_stats:
                course_stats[course_name] = {"total": 0, "paid": 0, "unpaid": 0}

            course_stats[course_name]["total"] += 1

            # Check payments for this student
            statuses = student_payments.get(student["id"], [])
            if any(s == "unpaid" for s in statuses):
                course_stats[course_name]["unpaid"] += 1
            else:
                # If student has payments and none are unpaid => consider paid
                if statuses:
                    course_stats[course_name]["paid"] += 1

        # Merge counts into courses
        for course in courses:
            stats = course_stats.get(course["name"], {"total": 0, "paid": 0, "unpaid": 0})
            course["total_students"] = stats["total"]
            course["paid_students"] = stats["paid"]
            course["unpaid_students"] = stats["unpaid"]

        return courses
    
    @staticmethod
    def get_by_name(course_name):
        response = supabase.table('courses').select('*').eq('name', course_name).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def create(name, description=None):
        """
        Creates a course/batch.
        """
        data = {'name': name}
        if description:
            data['description'] = description
        
        response = supabase.table('courses').insert(data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def update(course_id, name=None, description=None):
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description

        if not update_data:
            return None

        response = supabase.table('courses').update(update_data).eq('id', course_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def delete(course_id):
        response = supabase.table('courses').delete().eq('id', course_id).execute()
        return response.data
    @staticmethod
    def delete_with_students(course_id):
        """
        Deletes a course and all its students + payments in that course.
        """

        # 1. Get the course
        course_resp = supabase.table('courses').select('*').eq('id', course_id).execute()
        if not course_resp.data:
            return {"error": "Course not found"}

        course = course_resp.data[0]
        course_name = course['name']

        # 2. Get all students in this course
        students_resp = supabase.table('students').select('id').eq('course', course_name).execute()
        students = students_resp.data or []

        # 3. If students exist, delete their payments first
        if students:
            student_ids = [s['id'] for s in students]

            # Delete payments for these students
            supabase.table('payments').delete().in_('student_id', student_ids).execute()

            # Delete students
            supabase.table('students').delete().in_('id', student_ids).execute()

        # 4. Delete the course
        supabase.table('courses').delete().eq('id', course_id).execute()

        return {"success": True, "deleted_students": len(students)}
class Payment:
    @staticmethod
    def get_all():
        all_data = []
        last_id = 0
        chunk_size = 1000

        while True:
            response = (
                supabase.table("payments")
                .select("*, students(name, phone, course)")  # include course name
                .gt("id", last_id)
                .order("id")
                .limit(chunk_size)
                .execute()
            )

            data = response.data or []
            if not data:
                break

            all_data.extend(data)
            last_id = data[-1]["id"]

            print(f"Fetched {len(data)} records (total so far: {len(all_data)})")

            if len(data) < chunk_size:
                break

        print("Final length of payments:", len(all_data))
        return all_data

    @staticmethod
    def get_by_student_month_year(student_id, month, year):
        response = supabase.table('payments') \
            .select('*') \
            .eq('student_id', student_id) \
            .eq('month', month) \
            .eq('year', year) \
            .execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_by_student(student_id):
        response = supabase.table('payments').select('*').eq('student_id', student_id).execute()
        return response.data

    @staticmethod
    def create(student_id, month, year, status='paid'):
        response = supabase.table('payments').insert({
            'student_id': student_id,
            'month': month,
            'year': year,
            'status': status
        }).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def update(payment_id, status):
        response = supabase.table('payments').update({
            'status': status
        }).eq('id', payment_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_unpaid_students(month, year):
        response = supabase.table('payments').select('*, students(name, phone, email, course)') \
            .eq('month', month).eq('year', year).eq('status', 'unpaid').execute()
        return response.data

    @staticmethod
    def get_all_unpaid_students():
        response = supabase.table('payments')\
            .select('id, month, year, student_id, status, students(id, name, phone, email, course)')\
            .eq('status', 'unpaid')\
            .execute()
        
        data = response.data or []
        students_dict = {}

        for payment in data:
            student = payment.get('students')
            if not student:
                continue

            student_id = student['id']
            if student_id not in students_dict:
                students_dict[student_id] = {
                    'students': student,
                    'dues': []
                }
            students_dict[student_id]['dues'].append({
                'month': payment['month'],
                'year': payment['year']
            })
        
        return list(students_dict.values())
    
    # Add this method to the Payment class
    @staticmethod
    def get_unpaid_by_student(student_id):
        response = supabase.table('payments')\
            .select('*')\
            .eq('student_id', student_id)\
            .eq('status', 'unpaid')\
            .execute()
        return response.data
