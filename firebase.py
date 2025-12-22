

import firebase_admin
from firebase_admin import credentials, firestore, storage
from typing import Dict, List, Any, Optional
import cv2
import numpy as np
from datetime import datetime


# Initialize Firebase (do this once at app startup)
def initialize_firebase(credentials_path: str = 'serviceAccountKey.json', 
                       storage_bucket: str = None):
    
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            
            if storage_bucket:
                firebase_admin.initialize_app(cred, {
                    'storageBucket': storage_bucket
                })
            else:
                firebase_admin.initialize_app(cred)
            
            print("✅ Firebase initialized successfully")
        else:
            print("✅ Firebase already initialized")
            
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        raise


# Get Firebase instances
db = None
bucket = None

def get_db():
    """Get Firestore client"""
    global db
    if db is None:
        db = firestore.client()
    return db

def get_bucket():
    """Get Storage bucket"""
    global bucket
    if bucket is None:
        bucket = storage.bucket()
    return bucket


class FirestoreManager:
    
    @staticmethod
    def get_art(art_id: str) -> Optional[Dict[str, Any]]:
        
        try:
            doc_ref = get_db().collection("art").document(art_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                print(f"⚠️  Art not found: {art_id}")
                return None
                
        except Exception as e:
            print(f"❌ Failed to get art: {e}")
            raise Exception(f"Failed to get art: {e}")
    
    @staticmethod
    def update_status(art_id: str, status: str, message: str = None, **kwargs) -> None:
       
        try:
            doc_ref = get_db().collection("art").document(art_id)
            
            update_data = {
                'status': status,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                **kwargs
            }
            
            if message:
                update_data['message'] = message
            
            doc_ref.update(update_data)
            print(f"✅ Status updated: {art_id} -> {status}")
            
        except Exception as e:
            print(f"❌ Failed to update status: {e}")
            raise Exception(f"Failed to update status: {e}")
    
    @staticmethod
    def update_progress(art_id: str, progress: float, threads_completed: int, 
                       **kwargs) -> None:
        
        try:
            doc_ref = get_db().collection("art").document(art_id)
            
            update_data = {
                'progress': progress,
                'threadsCompleted': threads_completed,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                **kwargs
            }
            
            doc_ref.update(update_data)
            
        except Exception as e:
            print(f"❌ Failed to update progress: {e}")
            raise Exception(f"Failed to update progress: {e}")
    
    @staticmethod
    def create_thread_batch(art_id: str, iteration: int, threads: List[int]) -> None:
        
        try:
            doc_ref = (
                get_db().collection("art")
                .document(art_id)
                .collection("threads")
                .document(f"batch_{iteration}")
            )
            
            batch_data = {
                'iteration': iteration,
                'threads': threads,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.set(batch_data)
            print(f"✅ Thread batch saved: {art_id} - iteration {iteration}")
            
        except Exception as e:
            print(f"❌ Failed to save thread batch: {e}")
            raise Exception(f"Failed to save thread batch: {e}")
    
    @staticmethod
    def save_all_threads(art_id: str, threads: List[int]) -> None:
        
        try:
            doc_ref = (
                get_db().collection("art")
                .document(art_id)
                .collection("threads")
                .document("all_threads")
            )
            
            data = {
                'threads': threads,
                'totalCount': len(threads),
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.set(data)
            print(f"✅ All threads saved: {art_id} - {len(threads)} threads")
            
        except Exception as e:
            print(f"❌ Failed to save all threads: {e}")
            raise Exception(f"Failed to save all threads: {e}")
    
    @staticmethod
    def mark_completed(art_id: str, output_url: str, total_threads: int) -> None:
       
        try:
            doc_ref = get_db().collection("art").document(art_id)
            
            update_data = {
                'status': 'completed',
                'progress': 100,
                'outputUrl': output_url,
                'totalThreads': total_threads,
                'completedAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            print(f"✅ Art marked as completed: {art_id}")
            
        except Exception as e:
            print(f"❌ Failed to mark completed: {e}")
            raise Exception(f"Failed to mark completed: {e}")
    
    @staticmethod
    def mark_failed(art_id: str, error_message: str) -> None:
       
        try:
            doc_ref = get_db().collection("art").document(art_id)
            
            update_data = {
                'status': 'failed',
                'message': error_message,
                'failedAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            print(f"⚠️  Art marked as failed: {art_id}")
            
        except Exception as e:
            print(f"❌ Failed to mark failed: {e}")
            raise Exception(f"Failed to mark failed: {e}")


class StorageManager:
    """Manage Firebase Storage operations"""
    
    @staticmethod
    def upload_image_from_array(art_id: str, image_array: np.ndarray, 
                                folder: str = "string_art") -> str:
       
        try:
            # Encode image to PNG
            success, buffer = cv2.imencode('.png', image_array)
            if not success:
                raise Exception("Failed to encode image")
            
            # Upload to Firebase Storage
            filename = f"{folder}/{art_id}.png"
            blob = get_bucket().blob(filename)
            
            blob.upload_from_string(
                buffer.tobytes(),
                content_type='image/png'
            )
            
            # Make public
            blob.make_public()
            
            url = blob.public_url
            print(f"✅ Image uploaded: {url}")
            return url
            
        except Exception as e:
            print(f"❌ Failed to upload image: {e}")
            raise Exception(f"Failed to upload image: {e}")
    
    @staticmethod
    def upload_image_from_bytes(art_id: str, image_bytes: bytes,
                               folder: str = "string_art") -> str:
        
        try:
            filename = f"{folder}/{art_id}.png"
            blob = get_bucket().blob(filename)
            
            blob.upload_from_string(
                image_bytes,
                content_type='image/png'
            )
            
            blob.make_public()
            
            url = blob.public_url
            print(f"✅ Image uploaded: {url}")
            return url
            
        except Exception as e:
            print(f"❌ Failed to upload image: {e}")
            raise Exception(f"Failed to upload image: {e}")
    
    @staticmethod
    def upload_image_from_file(art_id: str, file_path: str,
                              folder: str = "string_art") -> str:
        
        try:
            filename = f"{folder}/{art_id}.png"
            blob = get_bucket().blob(filename)
            
            blob.upload_from_filename(file_path)
            blob.make_public()
            
            url = blob.public_url
            print(f"✅ Image uploaded: {url}")
            return url
            
        except Exception as e:
            print(f"❌ Failed to upload image: {e}")
            raise Exception(f"Failed to upload image: {e}")


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

"""
# 1. Initialize Firebase (do this once at app startup)
initialize_firebase(
    credentials_path='firebase-credentials.json',
    storage_bucket='your-project-id.appspot.com'
)

# 2. Get art data
art_data = FirestoreManager.get_art('art_123')
print(art_data['title'])

# 3. Update status
FirestoreManager.update_status(
    art_id='art_123',
    status='processing',
    message='Generating string art...'
)

# 4. Update progress (every 50 threads)
FirestoreManager.update_progress(
    art_id='art_123',
    progress=50.0,
    threads_completed=1750,
    reduction=0.85,
    currentIteration=1750
)

# 5. Save thread batch (every 50 threads)
FirestoreManager.create_thread_batch(
    art_id='art_123',
    iteration=1750,
    threads=[45, 122, 67, 89, ...]  # Last 50 threads
)

# 6. Upload final image
output_url = StorageManager.upload_image_from_array(
    art_id='art_123',
    image_array=final_image_array
)

# 7. Save all threads
FirestoreManager.save_all_threads(
    art_id='art_123',
    threads=[0, 45, 122, 67, 89, ...]  # All threads
)

# 8. Mark as completed
FirestoreManager.mark_completed(
    art_id='art_123',
    output_url=output_url,
    total_threads=3500
)

# 9. Mark as failed (if error occurs)
FirestoreManager.mark_failed(
    art_id='art_123',
    error_message='Image download failed'
)
"""