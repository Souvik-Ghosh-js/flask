import os
import dotenv
dotenv.load_dotenv()
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-please-change")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
    TWILIO_API_KEY = os.getenv("TWILIO_API_KEY")
    TWILIO_API_SECRET = os.getenv("TWILIO_API_SECRET")
