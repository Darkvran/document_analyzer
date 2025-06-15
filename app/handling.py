import re
from app.data import database
import math
from bson import ObjectId


# Функция для обновления статистик слов в БД.
# При каждом добавлении или удалении нового документа, вызывается эта функция, которая обновляет статистику.
def recalculate_idf(collection_id: str):
    collection_id_obj = ObjectId(collection_id)
    documents = list(database.documents.find({"collection_id": collection_id_obj}))
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
        database.documents.update_one(
            {"_id": doc["_id"]}, {"$set": {"words": updated_words}}
        )


# Функция обработки и сохраения документа в БД при его загрузке.
def file_handling(
    content: str, filename: str, collection_id: str, user_id: str
) -> list:
    words_list = re.split(
        r"\W+", content.lower()
    )  # Уменьшаем все содержимое документа до нижнего регистра
    words_num = len(words_list)
    count = {}

    for word in words_list:
        if word:
            count[word] = count.get(word, 0) + 1  # Подсчет количества каждого слова

    sorted_values = sorted(count.items(), key=lambda tpl: tpl[1], reverse=True)[
        :50
    ]  # Сортируем слова по убыванию их количества (топ 50)
    tf_dict = {word: freq / words_num for word, freq in sorted_values}
    words = [{"word": word, "tf": tf} for word, tf in tf_dict.items()]

    document = {
        "filename": filename,
        "content": content,
        "words_num": words_num,
        "words": words,
        "collection_id": ObjectId(collection_id),
        "user_id": ObjectId(user_id),
    }
    inserted_doc = database.documents.insert_one(document)
    database.collections.update_one(
        {"_id": ObjectId(collection_id)},
        {"$addToSet": {"doc_ids": inserted_doc.inserted_id}},
    )
    recalculate_idf(collection_id)

    updated_doc = database.documents.find_one({"_id": inserted_doc.inserted_id})
    result = [
        {
            "word": word["word"],
            "tf": round(word["tf"], 4),
            "idf": round(word.get("idf", 0), 4),
        }
        for word in sorted(
            updated_doc["words"], key=lambda w: w.get("idf", 0), reverse=True
        )
    ]
    return result
