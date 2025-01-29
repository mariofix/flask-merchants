import os

from store import create_app

app = create_app(os.getenv("FLASK_APP_SETTINGS_FILE", None))
