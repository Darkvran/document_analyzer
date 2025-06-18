from dotenv import load_dotenv
import os

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path, override=True)


FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")
ALLOWED_EXTENSIONS = os.getenv("APP_ALLOWED_EXTENSIONS")
VERSION = os.getenv("APP_VERSION")
FLASK_HOST = os.getenv("FLASK_HOST")
FLASK_PORT = os.getenv("FLASK_PORT")
FLASK_IS_DEBUG = os.getenv("FLASK_DEBUG")
