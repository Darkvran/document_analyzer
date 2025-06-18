import re
from app.data import database
from bson import ObjectId

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
    database.recalculate_idf(collection_id)

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
