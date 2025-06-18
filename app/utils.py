from app.config import ALLOWED_EXTENSIONS

# Функция проверки расширения файла на допустимость обработки
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS