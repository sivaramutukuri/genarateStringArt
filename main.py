import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv


from firebase import initialize_firebase
from v1 import startGenarate

app = Flask(__name__)
CORS(app)

load_dotenv()  # loads variables from .env file


storage_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")

initialize_firebase(storage_bucket=storage_bucket)

@app.get("/")
def read_root():
    return {"message": "Hello String Art APIS"}



@app.post("/generate/<art_id>")
def generate_string_art(art_id):
    startGenarate(art_id)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
