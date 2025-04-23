import re
from data import DataBase
import math

db = DataBase('docs.db')


def file_handling(content: str, filename: str) -> list:
    words_list = re.split('\W', content.lower())
    words_num = len(words_list)
    count = {}
    for element in words_list:
        if count.get(element):
            count[element] += 1
        else:
            if element != '':
                count[element] = 1

    sorted_values = sorted(count.items(), key=lambda tpl: tpl[1], reverse=True)
    tf_dict = {element[0]: element[1] / words_num for element in sorted_values}

    db.insert_document_with_words(filename, words_num, tf_dict)
    top_words = db.get_top_words_for_document(filename)
    idf_map = {
        word: math.log(db.get_documents_count() / max(1, db.get_document_frequency(word)))
        for word, _ in top_words
    }
    words_result = [{'word': word, 'tf': round(tf, 4), 'idf': round(idf_map[word], 4)} for word, tf in top_words]
    return words_result