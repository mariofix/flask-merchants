import os

from dotenv import load_dotenv

from store import create_app

load_dotenv()


app = create_app(os.getenv("FLASK_APP_SETTINGS_FILE", None))
