import os
from fastapi import BackgroundTasks, FastAPI, HTTPException
from dotenv import load_dotenv
import uvicorn

from models.device_model import ArtProgressRequest, DeviceCreate
from processer import StringArtProcessor
from supabase_manager import SupabaseService

# Load environment variables
load_dotenv()

app = FastAPI()

supabaseService = SupabaseService()


# -------------------- ROUTES --------------------

@app.get("/")
def root():
    return {"status": "online"}

    
@app.post("/generate/{artId}", status_code=202)
async def generate_art(artId: str, background_tasks: BackgroundTasks):
    
    background_tasks.add_task(run_processor_task, artId)
    return {"message": "Processing started", "artId": artId}

# @app.post("/upload", status_code=202)
# async def generate_art():
    
#   return  supabaseService.uploadImg('hus.png')


def run_processor_task(art_id: str):
    processor = StringArtProcessor(art_id)
    processor.process()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)



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