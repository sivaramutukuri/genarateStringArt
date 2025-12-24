from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from firebase_manager import FirebaseManager
from processor import StringArtProcessor

load_dotenv()
app = FastAPI(title="String Art API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Manager
firebase_manager = FirebaseManager()

def run_processor_task(art_id: str):
    processor = StringArtProcessor(art_id, firebase_manager)
    processor.process()

@app.get("/")
async def root():
    return {"status": "online", "engine": "FastAPI"}

@app.post("/generate/{art_id}", status_code=202)
async def generate_art(art_id: str, background_tasks: BackgroundTasks):
    art = firebase_manager.get_art(art_id)
    if not art:
        raise HTTPException(status_code=404, detail="Art ID not found in Firestore")
    
    # Run long-running process in background
    background_tasks.add_task(run_processor_task, art_id)
    
    return {
        "success": True, 
        "art_id": art_id, 
        "message": "Processing started in background"
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)