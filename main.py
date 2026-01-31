import os
from fastapi import BackgroundTasks, FastAPI, HTTPException
from dotenv import load_dotenv
import uvicorn

from firebase_service import FirebaseService
from models.device_model import  ArtResponse, DeviceCreate
from v2 import StringArtProcessor
# from supabase_manager import SupabaseService

# Load environment variables
load_dotenv()

app = FastAPI()

# supabaseService = SupabaseService()
firebaseService = FirebaseService()


# -------------------- ROUTES --------------------

@app.get("/")
@app.head("/")
def root():
    return {"status": "online"}

    
@app.post("/genarate/{artId}", status_code=202)
async def generate_art(artId: str, background_tasks: BackgroundTasks):
    
    background_tasks.add_task(run_processor_task, artId)
    return {"message": "Processing started", "artId": artId}

@app.post("/upload", status_code=202)
async def generate_art():
        try:
            return  firebaseService.addResponse({
                "deviceID": "N0oQsfWpA9BwcknuiYfJ",
                "userID": "JpGJAmy7NUOr74WmFZZvaCORNKh1",
                "request": {
                    "image": "user_789/20241228_123456.png",
                    "canvaSize": 512,
                    "margin": 20,
                    "nailCount": 200,
                    "threadCount": 3500,
                    "lineDarkness": 30,
                    "lightnessPenalty": 0.3,
                    "backGroundEnabled": False
                },
                "status": {
                    "threads": [],
                    "iteration": 0,
                    "status": "pending",
                    "message": "Art generation queued",
                    "progress": 0.0
                },
                "response": {
                    "threadCount": 606,
                    "threadIndex": [],
                    "nailCount": 200,
                    "nailIndex": [],
                    "image": "user_789/20241228_123456.png"
                }
            })
        except Exception as e:
            return f"{e}" 
        

@app.post("/updateDoc/{artID}")
async def generate_art(artID: str, body: ArtResponse):
    try:
        firebaseService.artID = artID
        return firebaseService.updateFinalResponse(body)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def run_processor_task(art_id: str):
    processor = StringArtProcessor(art_id)
    processor.process()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port,reload=False)



# import os
# from fastapi import BackgroundTasks, FastAPI, HTTPException
# from dotenv import load_dotenv
# import uvicorn

# from models.device_model import ArtProgressRequest, DeviceCreate
# from processer import StringArtProcessor
# from supabase_manager import SupabaseService

# # Load environment variables
# load_dotenv()

# app = FastAPI()

# supabaseService = SupabaseService()



# # -------------------- ROUTES --------------------

# @app.get("/")
# def root():
#     return {"status": "online"}

    
# @app.post("/generate/{artId}", status_code=202)
# async def generate_art(artId: str, background_tasks: BackgroundTasks):

#         if not artId:
#             raise HTTPException(status_code=404, detail="Art ID not found in Firestore")
        
#         background_tasks.add_task(run_processor_task, artId)

# def run_processor_task(art_id: str):
#     processor = StringArtProcessor(art_id)
#     processor.process()

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 5000))
#     uvicorn.run(app, host="0.0.0.0", port=port)