from flask import Flask, jsonify
from flask_cors import CORS

from firebase import initialize_firebase
from v1 import startGenarate

app = Flask(__name__)
CORS(app)


# Initialize Firebase on startup
initialize_firebase(
    credentials_path='serviceAccountKey.json',
    storage_bucket='your-project-id.appspot.com'  # Replace with your bucket
)


@app.get("/")
def read_root():
    return {"message": "Hello String Art APIS"}



@app.post("/generate/<art_id>")
def generate_string_art(art_id):
    startGenarate(art_id)