from app import create_app
from app.config import FLASK_HOST, FLASK_PORT, FLASK_IS_DEBUG

# Точка входа в приложение и создание его экземпляра.
app = create_app()

if __name__ == "__main__":
    app.run(
        FLASK_HOST,
        FLASK_PORT,
        FLASK_IS_DEBUG
    )
    