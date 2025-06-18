from pymongo import MongoClient
from flask_login import UserMixin
import math
from app.config import MONGODB_URI, MONGODB_DB_NAME
from bson import ObjectId

class User(UserMixin):
    def __init__(self, id: int, username: str, collections: list[str] = None):
        self.id = id
        self.username = username
        self.collections = collections

    def get_id(self):
        return str(self.id)


# Класс базы данных. Создан для удобства и единоразового подключения к базе данных.
# Чуть ниже мы создаем экземпляр, который и импортируем во все необходимые места.
class DataBase:

    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DB_NAME]
        self.documents = self.db["documents"]
        self.users = self.db["users"]
        self.collections = self.db["collections"]
        self.metrics = self.db["metrics"]

    # Функция для обновления статистик слов в БД.
    # При каждом добавлении или удалении нового документа, вызывается эта функция, которая обновляет статистику в пределах измененной коллекции.
    def recalculate_idf(self, collection_id: str):
        collection_id_obj = ObjectId(collection_id)
        documents = list(self.documents.find({"collection_id": collection_id_obj}))
        total_docs = len(documents)

        word_document_counts = {}
        for doc in documents:
            unique_words = set(word["word"] for word in doc.get("words", []))
            for word in unique_words:
                word_document_counts[word] = word_document_counts.get(word, 0) + 1

        idf_map = {
            word: math.log((total_docs + 1) / (df + 1)) + 1
            for word, df in word_document_counts.items()
        }

        for doc in documents:
            updated_words = []
            for word in doc.get("words", []):
                word["idf"] = idf_map.get(word["word"], 0)
                updated_words.append(word)
            self.documents.update_one(
                {"_id": doc["_id"]}, {"$set": {"words": updated_words}}
            )


database = DataBase()
