import sqlite3

class DataBase:
    def __init__(self, name):
        self.connection = sqlite3.connect(name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                words_num INTEGER
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS DocumentWords (
                doc_id INTEGER,
                word_id INTEGER,
                tf REAL,
                FOREIGN KEY(doc_id) REFERENCES Documents(id),
                FOREIGN KEY(word_id) REFERENCES Words(id),
                PRIMARY KEY(doc_id, word_id)
            )
        ''')
        self.connection.commit()

    def insert_document(self, filename: str, words_num: int) -> int:
        self.cursor.execute(
            "INSERT OR IGNORE INTO Documents (filename, words_num) VALUES (?, ?)",
            (filename, words_num)
        )
        self.connection.commit()
        self.cursor.execute("SELECT id FROM Documents WHERE filename = ?", (filename,))
        return self.cursor.fetchone()[0]

    def get_documents_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM Documents")
        return self.cursor.fetchone()[0]
    
    def insert_word(self, word: str) -> int:
        self.cursor.execute(
            "INSERT OR IGNORE INTO Words (word) VALUES (?)", (word,)
        )
        self.connection.commit()
        self.cursor.execute("SELECT id FROM Words WHERE word = ?", (word,))
        return self.cursor.fetchone()[0]
    
    def insert_tf(self, doc_id: int, word_id: int, tf: float):
        self.cursor.execute(
            "INSERT OR REPLACE INTO DocumentWords (doc_id, word_id, tf) VALUES (?, ?, ?)",
            (doc_id, word_id, tf)
        )
        self.connection.commit()

    def get_document_frequency(self, word: str) -> int:
        """Считает количество документов, содержащих слово"""
        self.cursor.execute(
            "SELECT id FROM Words WHERE word = ?", (word,)
        )
        result = self.cursor.fetchone()
        if result is None:
            return 0
        word_id = result[0]
        self.cursor.execute(
            "SELECT COUNT(*) FROM DocumentWords WHERE word_id = ?", (word_id,)
        )
        return self.cursor.fetchone()[0]
    
    def insert_document_with_words(self, filename: str, words_num: int, tf_data: dict[str, float]):
        doc_id = self.insert_document(filename, words_num)
        for word, tf in tf_data.items():
            word_id = self.insert_word(word)
            self.insert_tf(doc_id, word_id, tf)

    def get_top_words_for_document(self, filename: str, limit: int = 50) -> list[tuple[str, float]]:
        self.cursor.execute("SELECT id FROM Documents WHERE filename = ?", (filename,))
        result = self.cursor.fetchone()
        if result is None:
            return []
        doc_id = result[0]

        self.cursor.execute('''
            SELECT w.word, dw.tf
            FROM DocumentWords dw
            JOIN Words w ON dw.word_id = w.id
            WHERE dw.doc_id = ?
            ORDER BY dw.tf DESC
            LIMIT ?
        ''', (doc_id, limit))
        return self.cursor.fetchall()