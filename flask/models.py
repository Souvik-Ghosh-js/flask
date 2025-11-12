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
    def get_by_phone(phone):
        """Get all students with this phone number"""
        response = supabase.table('students').select('*, course').eq('phone', phone).execute()
        return response.data or []

    @staticmethod
    def get_by_phone_and_batch(phone, batch):
        """Get student by phone number and batch"""
        response = supabase.table('students').select('*, course').eq('phone', phone).eq('course', batch).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def create(name, phone, course=None, email=None):
        # Check if student with same phone already exists in this batch
        existing_student = Student.get_by_phone_and_batch(phone, course)
        if existing_student:
            raise Exception(f"Student with phone {phone} already exists in batch {course}")
        
        data = {
            'name': name,
            'phone': phone,
            'course': course,
            'email': email
        }
        data = {k: v for k, v in data.items() if v is not None}

        response = supabase.table('students').insert(data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def update(student_id, name=None, phone=None, email=None, course=None):
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
        courses_response = supabase.table('courses').select('*').execute()
        courses = courses_response.data or []

        students_response = supabase.table('students').select('id, name, course').execute()
        students = students_response.data or []

        payments_response = supabase.table('payments').select('student_id, status').execute()
        payments = payments_response.data or []

        student_payments = {}
        for p in payments:
            sid = p["student_id"]
            if sid not in student_payments:
                student_payments[sid] = []
            student_payments[sid].append(p["status"])

        course_stats = {}
        for student in students:
            course_name = student.get("course")
            if not course_name:
                continue

            if course_name not in course_stats:
                course_stats[course_name] = {"total": 0, "paid": 0, "unpaid": 0}

            course_stats[course_name]["total"] += 1

            statuses = student_payments.get(student["id"], [])
            if any(s == "unpaid" for s in statuses):
                course_stats[course_name]["unpaid"] += 1
            else:
                if statuses:
                    course_stats[course_name]["paid"] += 1

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
        course_resp = supabase.table('courses').select('*').eq('id', course_id).execute()
        if not course_resp.data:
            return {"error": "Course not found"}

        course = course_resp.data[0]
        course_name = course['name']

        students_resp = supabase.table('students').select('id').eq('course', course_name).execute()
        students = students_resp.data or []

        if students:
            student_ids = [s['id'] for s in students]
            supabase.table('payments').delete().in_('student_id', student_ids).execute()
            supabase.table('students').delete().in_('id', student_ids).execute()

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
                .select("*, students(name, phone, course)")
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

            if len(data) < chunk_size:
                break

        return all_data

    @staticmethod
    def get_by_student_month_year_batch(student_id, month, year, batch):
        response = supabase.table('payments') \
            .select('*, students(course)') \
            .eq('student_id', student_id) \
            .eq('month', month) \
            .eq('year', year) \
            .execute()
        
        payments = response.data or []
        for payment in payments:
            if payment.get('students', {}).get('course') == batch:
                return payment
        return None

    @staticmethod
    def get_by_student(student_id):
        response = supabase.table('payments').select('*').eq('student_id', student_id).execute()
        return response.data

    @staticmethod
    def create(student_id, month, year, status='paid', batch=None):
        # Check if payment already exists for this student, month, year, AND batch
        if batch:
            existing = Payment.get_by_student_month_year_batch(student_id, month, year, batch)
            if existing:
                raise Exception(f"Payment already exists for this student in {month} {year} for batch {batch}")
        
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
    def get_unpaid_students(month, year, batch=None):
        response = supabase.table('payments').select('*, students(name, phone, email, course)') \
            .eq('month', month).eq('year', year).eq('status', 'unpaid').execute()
        
        data = response.data or []
        if batch:
            data = [p for p in data if p.get('students', {}).get('course') == batch]
        
        return data

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

    @staticmethod
    def get_unpaid_by_student(student_id):
        response = supabase.table('payments')\
            .select('*')\
            .eq('student_id', student_id)\
            .eq('status', 'unpaid')\
            .execute()
        return response.data
    
    @staticmethod
    def bulk_create(payments_data):
        """Bulk create multiple payments"""
        try:
            print(f"Bulk creating {len(payments_data)} payments...")
            
            # Prepare data for bulk insert - WITHOUT batch column
            insert_data = []
            for payment in payments_data:
                payment_data = {
                    'student_id': payment['student_id'],
                    'month': payment['month'],
                    'year': payment['year'],
                    'status': payment['status']
                }
                # Remove batch since it doesn't exist in the table
                insert_data.append(payment_data)
            
            # Execute bulk insert
            response = supabase.table('payments').insert(insert_data).execute()
            
            if hasattr(response, 'error') and response.error:
                print(f"Bulk create error: {response.error}")
                return 0
                
            return len(response.data) if response.data else 0
            
        except Exception as e:
            print(f"Bulk create exception: {e}")
            return 0

    @staticmethod
    def bulk_update(updates_data):
        """Bulk update multiple payments"""
        try:
            print(f"Bulk updating {len(updates_data)} payments...")
            
            success_count = 0
            
            # Process updates in smaller batches to avoid timeouts
            batch_size = 50
            for i in range(0, len(updates_data), batch_size):
                batch = updates_data[i:i + batch_size]
                
                for update in batch:
                    try:
                        response = supabase.table('payments').update({
                            'status': update['status']
                        }).eq('id', update['payment_id']).execute()
                        
                        if not (hasattr(response, 'error') and response.error):
                            success_count += 1
                            
                    except Exception as e:
                        print(f"Error updating payment {update['payment_id']}: {e}")
                        continue
            
            return success_count
            
        except Exception as e:
            print(f"Bulk update exception: {e}")
            return 0

    @staticmethod
    def bulk_upsert(payments_data):
        """Bulk insert or update payments using upsert"""
        try:
            print(f"Bulk upserting {len(payments_data)} payments...")
            
            # Prepare data for upsert
            insert_data = []
            for payment in payments_data:
                payment_data = {
                    'student_id': payment['student_id'],
                    'month': payment['month'],
                    'year': payment['year'],
                    'status': payment['status']
                }
                insert_data.append(payment_data)
            
            # Use upsert with on_conflict to handle duplicates
            response = supabase.table('payments').upsert(
                insert_data,
                on_conflict='student_id,month,year'
            ).execute()
            
            if hasattr(response, 'error') and response.error:
                print(f"Bulk upsert error: {response.error}")
                return 0
                
            return len(response.data) if response.data else 0
            
        except Exception as e:
            print(f"Bulk upsert exception: {e}")
            return 0
        
    @staticmethod
    def get_payments_for_batch(batch_name):
        """Get all payments for students in a specific batch"""
        try:
            all_payments = []
            page = 0
            page_size = 1000
            
            while True:
                response = supabase.table('payments')\
                    .select('*, students(name, phone, course)')\
                    .eq('students.course', batch_name)\
                    .range(page * page_size, (page + 1) * page_size - 1)\
                    .execute()
                
                if not response.data:
                    break
                    
                all_payments.extend(response.data)
                
                if len(response.data) < page_size:
                    break
                    
                page += 1
                
            return all_payments
            
        except Exception as e:
            print(f"Error getting payments for batch: {e}")
            return []
    