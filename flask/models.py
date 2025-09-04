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
    def get_by_id(student_id):
        response = supabase.table('students').select('*').eq('id', student_id).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def create(name, phone, email):
        response = supabase.table('students').insert({
            'name': name,
            'phone': phone,
            'email': email
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
        response = (
            supabase.table("payments")
            .select("*, students(name)")
            .execute()
        )
        return response.data

    
    @staticmethod
    def get_by_student(student_id):
        response = supabase.table('payments').select('*').eq('student_id', student_id).execute()
        return response.data
    
    @staticmethod
    def create(student_id, month, year, amount, status='paid'):
        response = supabase.table('payments').insert({
            'student_id': student_id,
            'month': month,
            'year': year,
            'amount': amount,
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