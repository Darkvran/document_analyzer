from app import create_app
from dotenv import load_dotenv
import os

load_dotenv()
# Точка входа в приложение и создание его экземпляра.
app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST"),
        port=os.getenv("FLASK_PORT"),
        debug=os.getenv("FLASK_DEBUG"),
    )
