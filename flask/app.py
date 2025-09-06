from flask import Flask
from config import Config
from routes import routes_bp   # import blueprint
import threading
import schedule
import time
from utils import check_and_send_reminders
import os
app = Flask(__name__)
app.config.from_object(Config)

# Register blueprint
app.register_blueprint(routes_bp)

# Background scheduler for automated reminders
def run_scheduler():
    schedule.every().day.at("18:59").do(check_and_send_reminders)  # Run at end of day
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start the scheduler in a separate thread
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host='0.0.0.0', port=port)
