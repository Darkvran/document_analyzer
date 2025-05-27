from pymongo import MongoClient
from datetime import datetime
import statistics, os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

class MetricsCollector:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.client[os.getenv("MONGODB_DB_NAME")]
        self.collection = self.db["metrics"]

        if self.collection.count_documents({}) == 0:
            self.collection.insert_one({
                "files_processed": 0,
                "processing_times": [],
                "latest_file_processed_timestamp": None
            })

    def register_file_processed(self, processing_time: float):
        doc = self.collection.find_one()
        doc["files_processed"] += 1
        doc["processing_times"].append(processing_time)
        doc["latest_file_processed_timestamp"] = datetime.now().isoformat()
        self.collection.replace_one({}, doc)

    def get_metrics(self):
        doc = self.collection.find_one()
        times = doc.get("processing_times", [])

        if not times:
            return {
                "files_processed": 0,
                "min_time_processed": None,
                "avg_time_processed": None,
                "max_time_processed": None,
                "latest_file_processed_timestamp": None,
                "std_dev_processing_time": None,
                "median_processing_time": None
            }

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        median = statistics.median(times)

        return {
            "files_processed": doc["files_processed"],
            "min_time_processed": round(min_time, 3),
            "avg_time_processed": round(avg_time, 3),
            "max_time_processed": round(max_time, 3),
            "latest_file_processed_timestamp": doc["latest_file_processed_timestamp"],
            "std_dev_processing_time": round(std_dev, 3),
            "median_processing_time": round(median, 3)
        }
