from data import DataBase, Document, database
import re
import math

def file_handling(content: str, filename: str) -> list:
    words_list = re.split(r'\W+', content.lower())
    words_num = len(words_list)
    count = {}

    for word in words_list:
        if word:
            count[word] = count.get(word, 0) + 1

    sorted_values = sorted(count.items(), key=lambda tpl: tpl[1], reverse=True)
    tf_dict = {word: freq / words_num for word, freq in sorted_values}
    words = [{"word": word, "tf": tf} for word, tf in tf_dict.items()]
    document = Document(filename, words_num, words)
    db.insert_document(document)

    top_words = db.get_top_words_for_document(filename)
    total_docs = db.get_documents_count()

    idf_map = {
        word: math.log(total_docs / max(1, db.get_document_frequency(word)))
        for word, _ in top_words
    }

    words_result = [{'word': word, 'tf': round(tf, 4), 'idf': round(idf_map[word], 4)} for word, tf in top_words]
    words_result.sort(key=lambda x: x['idf'], reverse=True)
    return words_result