from dotenv import load_dotenv
from store.app import create_app

load_dotenv()

app = create_app()

