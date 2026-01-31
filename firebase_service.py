import datetime
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore import ArrayUnion
import requests
import os

from models.device_model import  ArtRequest, ArtResponse, ArtStatus


class FirebaseService:
    def __init__(self,):
        self.artID :str
        load_dotenv()
        
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            # Option 1: Using service account file
            
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CERT_URL")
            })
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET")  # e.g., 'your-project.appspot.com'
            })
        
        self.db = firestore.client()
        self.bucket = storage.bucket()
        
        # Collection names
        self.arts = "arts"
        self.devices = "Devices"
        
        self.sp: ArtRequest = None

    def getArtRequest(self,artID:str) -> Optional[ArtRequest]:
        self.artID = artID
        try:
            doc_ref = self.db.collection(self.arts).document(self.artID)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                request = data.get('request')  
            
            self.sp = ArtRequest(**request)
            return self.sp
            
        except Exception as e:
            print(f"Error fetching art: {e}")
            return None
        

    def updateResponce(self, request: Dict[str,Any]):
        """Update status and append new threads to existing array"""
        try:
            doc_ref = self.db.collection(self.arts).document(self.artID)

            doc_ref.set({'progress':request}, merge=True)
            return True  

        except Exception as e:
            return f"{e}" 
        
    def addResponse(self, request: dict):
        """Update status and append new threads to existing array"""
        try:
            doc_ref = self.db.collection(self.arts)
            doc_ref.add(request)
            return True  
            
        except Exception as e:
            return f"{e}" 
        
    def updateFinalResponse(self, request: Dict[str,Any]):
        try:

            doc_ref = self.db.collection(self.arts).document(self.artID)
            
            final_data = {
               'result' : request
            }
            doc_ref.set(final_data, merge=True)
            return {"success": True}

        except Exception as e:
            raise RuntimeError(e)
    
    def downloadImage(self, img: str) -> bytes:
        try:
            blob = self.bucket.blob(img)
            if not blob.exists():
                raise Exception(f"File not found: {img}")
        
        # Download as bytes
            file_bytes = blob.download_as_bytes()
            return file_bytes

        except Exception as e:
             raise Exception(f"Error downloading image: {e}")
    
    def getPublicUrl(self, file_path: str) -> str:
        """Get public URL for a file in Firebase Storage"""
        try:
            blob = self.bucket.blob(file_path)
            # Make public if not already
            blob.make_public()
            return blob.public_url
        except Exception as e:
            raise Exception(f"Error getting public URL: {e}")
