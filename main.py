import os
from flask import Flask, jsonify
from flask_cors import CORS

from firebase import initialize_firebase
from v1 import startGenarate

app = Flask(__name__)
CORS(app)


initialize_firebase(storage_bucket="your-project-id.appspot.com")



@app.get("/")
def read_root():
    return {"message": "Hello String Art APIS"}



@app.post("/generate/<art_id>")
def generate_string_art(art_id):
    startGenarate(art_id)