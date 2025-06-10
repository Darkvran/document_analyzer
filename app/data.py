import os
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_login import UserMixin

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)



class Collection:
    pass
class Document:
    def __init__(self, filename: str, words_num: int, words: list[dict]):
        self.filename = filename
        self.words_num = words_num
        self.words = words
    def get_top_words_for_document(self,limit: int = 50) -> list[tuple[str, float]]:
        top_words = self.words.sort(key=lambda w: w["tf"], reverse=True)
        return [(entry["word"], entry["tf"]) for entry in top_words[:limit]]
    
class User(UserMixin):
    def __init__(self, id: int, username: str, collections: Collection = None):
        self.id = id
        self.username = username
        self.collections = collections

    def get_id(self):
        return str(self.id)
class DataBase:
    
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.client[os.getenv("MONGODB_DB_NAME")]
        self.documents = self.db["documents"]
        self.users = self.db["users"]

    def insert_document(self, document: Document):
        self.documents.update_one(
            {"filename": document.filename},
            {"$set": document.__dict__},
            upsert=True
        )

    def get_documents_count(self) -> int:
        return self.documents.count_documents({})

    def get_document_frequency(self, word: str) -> int:
        return self.documents.count_documents({
            "words.word": word
        })

    def get_top_words_for_document(self, filename: str, limit: int = 50) -> list[tuple[str, float]]:
        doc = self.documents.find_one({"filename": filename})
        if not doc or "words" not in doc:
            return []
        words = doc["words"]
        words.sort(key=lambda w: w["tf"], reverse=True)
        return [(entry["word"], entry["tf"]) for entry in words[:limit]]
    
database = DataBase()  
