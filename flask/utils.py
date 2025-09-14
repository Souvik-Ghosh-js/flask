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
            content_sid="HX2be022e1998ae9d83b0adb255ce1e3e3",  # Your approved template SID
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
            voice_sid = send_voice_reminder(phone, student_name, due_text)
            whatsapp_sid = send_whatsapp_reminder(phone, student_name, due_text ,custom_message=user_message) 

            print(f"Sent reminders to {student_name}: Voice SID - {voice_sid}, WhatsApp SID - {whatsapp_sid}")


from datetime import datetime
import calendar
from models import Payment, Student

def check_and_send_reminders_batch(user_message, batch=None, month=None):
    # Fetch all unpaid payments, optionally filtered by batch and month
    all_unpaid = Payment.get_all_unpaid_students()

    # Filter by batch and month if provided
    if batch or month:
        filtered_unpaid = []
        for student in all_unpaid:
            filtered_dues = [
                due for due in student['dues']
                if (not batch or student['students']['course'] == batch)
                and (not month or due['month'].lower() == month.lower())
            ]
            if filtered_dues:
                filtered_unpaid.append({
                    'students': student['students'],
                    'dues': filtered_dues
                })
        all_unpaid = filtered_unpaid

    # If no unpaid students match the filters, return
    if not all_unpaid:
        print("No unpaid dues found for the specified filters.")
        return []

    results = []
    default_message = user_message
    for student in all_unpaid:
        student_name = student['students']['name']
        phone = student['students']['phone']
        due_months = [f"{due['month']} {due['year']}" for due in student['dues']]
        due_text = ', '.join(due_months)

        # Format the message
        formatted_message = default_message

        try:
            # Send WhatsApp reminder
            whatsapp_sid = send_whatsapp_reminder(phone, student_name, due_text, custom_message=formatted_message)
            voice_sid = None
            try:
                # Send voice reminder (assumes this function exists)
                voice_sid = send_voice_reminder(phone, student_name, due_text)
            except Exception as e:
                print(f"Voice reminder failed for {student_name}: {str(e)}")

            print(f"Sent reminders to {student_name}: Voice SID - {voice_sid}, WhatsApp SID - {whatsapp_sid}")
            results.append({
                'phone': phone,
                'name': student_name,
                'status': 'sent',
                'whatsapp_sid': whatsapp_sid,
                'voice_sid': voice_sid
            })
        except Exception as e:
            print(f"Failed to send reminders to {student_name}: {str(e)}")
            results.append({
                'phone': phone,
                'name': student_name,
                'status': f'failed: {str(e)}'
            })

    return results

def send_whatsapp_announcement(phone_number, custom_message):
    """
    Send a WhatsApp announcement message using Twilio.
    phone_number: str (without +91)
    student_name: str
    custom_message: str (user typed message from Announcement page)
    """
    student_name = "Jibak"
    try:
        message = twilio_client.messages.create(
            from_=f"whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}",  # Your registered sender
            to=f"whatsapp:+91{phone_number}",                  # Recipient number
            content_sid="HXe674c3d6db6cc0ecd03000674abc1e9d",  # Your approved template SID
            content_variables=json.dumps({
                "1": student_name,   # placeholder 1
                "2": custom_message if custom_message else "Thank You!"  # placeholder 3
            })
        )
        print(f"Announcementss sent to {phone_number}, SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Error sending WhatsApp announcement: {e}")
        return None
