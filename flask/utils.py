from twilio.rest import Client
from config import Config
from datetime import datetime, timedelta
from models import Payment
import calendar
import json
twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

def send_voice_reminder(phone_number, student_name, month):
    try:
        call = twilio_client.calls.create(
            twiml=f'<Response><Say>Hello {student_name}, this is a reminder from your coaching center. Your payment for {month} is pending. Please make the payment at your earliest convenience. Thank you.</Say></Response>',
            to="+91" + phone_number,
            from_=Config.TWILIO_PHONE_NUMBER
        )
        return call.sid
    except Exception as e:
        print(f"Error sending voice call: {e}")
        return None

def send_whatsapp_reminder(phone_number, student_name, month):
    try:
        message = twilio_client.messages.create(
            from_=f"whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}",  # Your registered sender
            to=f"whatsapp:+91{phone_number}",                  # Recipient number
            content_sid="HXaf9fb3b04d620f2c20ddda0fe602c57a",  # Your approved template SID
            content_variables=json.dumps({
                "1": student_name,   # placeholder 1
                "2": month        # placeholder      # placeholder 3
            })
        )
        return message.sid
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return None


def check_and_send_reminders(force=False):
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    
    # Run only on last day OR if force=True
    if today.day == last_day or force:
        month = today.strftime('%B')
        year = today.year
        
        unpaid_students = Payment.get_unpaid_students(month, year)
        print(f"Unpaid students for {month} {year}: {unpaid_students}")
        
        for student in unpaid_students:
            # Send voice call
            voice_sid = send_voice_reminder(
                student['students']['phone'], 
                student['students']['name'], 
                month
            )
            
            whatsapp_sid = send_whatsapp_reminder(
                student['students']['phone'], 
                student['students']['name'], 
                month
            )
            
            # Log the reminders (you might want to store this in your database)
            print(f"Sent reminders to {student['students']['name']}: Voice SID - {whatsapp_sid}")

    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    
    # Check if today is the last day of the month
    if today.day == last_day:
        month = today.strftime('%B')
        year = today.year
        
        unpaid_students = Payment.get_unpaid_students(month, year)
        
        for student in unpaid_students:
            # Send voice call
            voice_sid = send_voice_reminder(
                student['students']['phone'], 
                student['students']['name'], 
                month
            )
            
            # Send WhatsApp message
            whatsapp_sid = send_whatsapp_reminder(
                student['students']['phone'], 
                student['students']['name'], 
                month
            )
            
            # Log the reminders (you might want to store this in your database)
            print(f"Sent reminders to {student['students']['name']}: Voice SID - {voice_sid}, WhatsApp SID - {whatsapp_sid}")