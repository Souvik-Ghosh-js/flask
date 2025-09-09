from supabase import create_client, Client
import os
from config import Config

supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

class Student:
    @staticmethod
    def get_all():
        response = supabase.table('students').select('*').execute()
        return response.data
    @staticmethod
    def get_by_name(name):
        response = supabase.table('students').select('*').eq('name', name).execute()
        return response.data[0] if response.data else None
    @staticmethod
    def get_by_id(student_id):
        response = supabase.table('students').select('*').eq('id', student_id).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def create(name, phone):
        response = supabase.table('students').insert({
            'name': name,
            'phone': phone,
        }).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def update(student_id, name, phone, email):
        response = supabase.table('students').update({
            'name': name,
            'phone': phone,
            'email': email
        }).eq('id', student_id).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def delete(student_id):
        response = supabase.table('students').delete().eq('id', student_id).execute()
        return response.data

class Payment:
    @staticmethod
    def get_all():
        all_data = []
        last_id = 0
        chunk_size = 1000

        while True:
            response = (
                supabase.table("payments")
                .select("*, students(name, phone)")   # include phone here
                .gt("id", last_id)
                .order("id")
                .limit(chunk_size)
                .execute()
            )


            data = response.data or []
            if not data:
                break

            all_data.extend(data)
            last_id = data[-1]["id"]  # update checkpoint

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
        response = supabase.table('payments').select('*, students(name, phone, email)').eq('month', month).eq('year', year).eq('status', 'unpaid').execute()
        return response.data
    

    @staticmethod
    def get_all_unpaid_students():
        # Fetch all unpaid payments along with student info
        response = supabase.table('payments')\
            .select('id, month, year, student_id, status, students(id, name, phone, email)')\
            .eq('status', 'unpaid')\
            .execute()
        
        data = response.data or []

        # Aggregate dues by student
        students_dict = {}
        for payment in data:
            student = payment.get('students')
            if not student:
                continue  # skip if student info missing

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
        
        # Return as a list
        return list(students_dict.values())
