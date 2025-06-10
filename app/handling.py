import re
from data import database
import math
from bson import ObjectId

def file_handling(content: str, filename: str, collection_id: str, user_id: str) -> list:
    words_list = re.split(r'\W+', content.lower())
    words_num = len(words_list)
    count = {}

    for word in words_list:
        if word:
            count[word] = count.get(word, 0) + 1

    sorted_values = sorted(count.items(), key=lambda tpl: tpl[1], reverse=True)[:50]
    tf_dict = {word: freq / words_num for word, freq in sorted_values}
    words = [{"word": word, "tf": tf} for word, tf in tf_dict.items()]
    
    # Создаем или обновляем документ с указанием collection_id
    document = {
        "filename": filename,
        "content": content,
        "words_num": words_num,
        "words": words,
        "collection_id": ObjectId(collection_id),
        "user_id": ObjectId(user_id)
    }
    inserted_doc = database.documents.insert_one(document)
    database.collections.update_one(
        {"_id": ObjectId(collection_id)},
        {"$addToSet": {"doc_ids": inserted_doc.inserted_id}}  # $addToSet чтобы не дублировать
    )
    # Получаем топ-слов с TF из документа
    top_words = sorted(words, key=lambda w: w["tf"], reverse=True)

    # Считаем количество документов в коллекции
    total_docs_in_collection = database.documents.count_documents({"collection_id": ObjectId(collection_id)})

    # IDF считаем по документам внутри коллекции
    idf_map = {}
    for word_entry in top_words:
        word = word_entry["word"]
        doc_freq = database.documents.count_documents({
            "collection_id": ObjectId(collection_id),
            "words.word": word
        })
        idf = math.log((total_docs_in_collection + 1) / (doc_freq + 1)) + 1  
        idf_map[word] = idf

    words_result = [
        {
            'word': word_entry['word'],
            'tf': round(word_entry['tf'], 4),
            'idf': round(idf_map[word_entry['word']], 4)
        }
        for word_entry in top_words
    ]

    words_result.sort(key=lambda x: x['idf'], reverse=True)

    return words_result
