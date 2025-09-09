from twilio.rest import Client
from config import Config
from datetime import datetime, timedelta
from models import Payment
import calendar
import json
twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

def send_voice_reminder(phone_number, student_name, month):
    try:
        audio_url = "https://fgksbxrxskwchjyqxpvx.supabase.co/storage/v1/object/public/mp3/whatsapp-audio-2025-09-07-at-115356-pm_6RDISKZK.mp3"

        call = twilio_client.calls.create(
            twiml=f'<Response><Play>{audio_url}</Play></Response>',
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
    print(f"Today's date: {today}, Last day of month: {last_day}, Force: {force}")
    
    # Run only on last day OR if force=True
    if today.day == last_day or force:
        # Get all students with any unpaid dues
        all_unpaid = Payment.get_all_unpaid_students()  # You need to implement this
        print(f"Students with any dues: {all_unpaid}")

        for student in all_unpaid:
            student_name = student['students']['name']
            phone = student['students']['phone']
            
            # Collect all months with dues
            due_months = [f"{due['month']} {due['year']}" for due in student['dues']]
            due_text = ', '.join(due_months)
            
            # Send only **one** voice call and **one** WhatsApp message
            voice_sid = send_voice_reminder(phone, student_name, due_text)
            whatsapp_sid = send_whatsapp_reminder(phone, student_name, due_text)
            
            # Log the reminders (store in DB if needed)
            print(f"Sent reminders to {student_name}: Voice SID - {voice_sid}, WhatsApp SID - {whatsapp_sid}")
