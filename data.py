import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class DataBase:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.client[os.getenv("MONGODB_DB_NAME")]
        self.documents = self.db["documents"]

    def insert_document_with_words(self, filename: str, words_num: int, tf_data: dict[str, float]):
        self.documents.update_one(
            {"filename": filename},
            {"$set": {
                "filename": filename,
                "words_num": words_num,
                "words": [{"word": word, "tf": tf} for word, tf in tf_data.items()]
            }},
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