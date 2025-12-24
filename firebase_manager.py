import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, storage
import numpy as np
import cv2
from typing import Dict, List, Any, Optional

class FirebaseManager:
    def __init__(self):
        if not firebase_admin._apps:
            service_account_info = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
            storage_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")
            
            if not service_account_info:
                raise Exception("FIREBASE_SERVICE_ACCOUNT not set")
                
            cred = credentials.Certificate(json.loads(service_account_info))
            firebase_admin.initialize_app(cred, {'storageBucket': storage_bucket})
        
        self.db = firestore.client()
        self.bucket = storage.bucket()

    def get_art(self, art_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection("art").document(art_id).get()
        return doc.to_dict() if doc.exists else None

    def update_status(self, art_id: str, status: str, **kwargs):
        data = {"status": status, "updatedAt": firestore.SERVER_TIMESTAMP, **kwargs}
        self.db.collection("art").document(art_id).update(data)

    def create_thread_batch(self, art_id: str, iteration: int, threads: List[int]):
        batch_ref = self.db.collection("art").document(art_id).collection("threads").document(f"batch_{iteration}")
        batch_ref.set({"iteration": iteration, "threads": threads, "timestamp": firestore.SERVER_TIMESTAMP})

    def upload_image(self, art_id: str, image_array: np.ndarray) -> str:
        success, buffer = cv2.imencode('.png', image_array)
        if not success: raise Exception("Encoding failed")
        
        blob = self.bucket.blob(f"string_art/{art_id}.png")
        blob.upload_from_string(buffer.tobytes(), content_type='image/png')
        blob.make_public()
        return blob.public_url

    def mark_completed(self, art_id: str, url: str, total: int, threads: List[int]):
        doc_ref = self.db.collection("art").document(art_id)
        doc_ref.update({
            'status': 'completed',
            'progress': 100,
            'outputUrl': url,
            'totalThreads': total,
            'completedAt': firestore.SERVER_TIMESTAMP
        })
        doc_ref.collection("threads").document("all_threads").set({
            "threads": threads, "totalCount": total
        })