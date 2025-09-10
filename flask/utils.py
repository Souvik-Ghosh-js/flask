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

def send_whatsapp_reminder(phone_number, student_name, month, custom_message=None):
    try:
        message = twilio_client.messages.create(
            from_=f"whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}",  # Your registered sender
            to=f"whatsapp:+91{phone_number}",                  # Recipient number
            content_sid="HX143094063df9d0f0636b04e401b0d5df",  # Your approved template SID
            content_variables=json.dumps({
                "1": student_name,   # placeholder 1
                "2": month,          # placeholder 2
                "3": custom_message if custom_message else "Thank You!"  # placeholder 3
            })
        )
        return message.sid
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return None

def check_and_send_reminders(force=False, user_message=None):
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]

    if today.day == last_day or force:
        all_unpaid = Payment.get_all_unpaid_students()

        for student in all_unpaid:
            student_name = student['students']['name']
            phone = student['students']['phone']
            due_months = [f"{due['month']} {due['year']}" for due in student['dues']]
            due_text = ', '.join(due_months)

            # Send reminders
            # voice_sid = send_voice_reminder(phone, student_name, due_text)
            whatsapp_sid = send_whatsapp_reminder(phone, student_name, due_text ,custom_message=user_message) 

            print(f"Sent reminders to {student_name}: Voice SID , WhatsApp SID - {whatsapp_sid}")

def send_whatsapp_announcement(phone_number, custom_message):
    """
    Send a WhatsApp announcement message using Twilio.
    phone_number: str (without +91)
    student_name: str
    custom_message: str (user typed message from Announcement page)
    """
    try:
        message = twilio_client.messages.create(
            from_=f"whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:+91{phone_number}",
            content_sid="HX1a6e4a6d1e6d6667a7c94a615a7c9429",  # <-- create new approved template for announcements
            content_variables=json.dumps({
                "1": custom_message
            })
        )
        return message.sid
    except Exception as e:
        print(f"Error sending WhatsApp announcement: {e}")
        return None
