# models/device_model.py
from typing import List, Optional
from pydantic import BaseModel


class DeviceCreate(BaseModel):
    fingerprint: str
    Model: str
    brand: str
    androidVersion: str


class ArtSpecifiactions(BaseModel):
    canvaSize: int = 512
    margin: int = 20
    nailCount: int = 200
    threadCount: int = 3500
    lineDarkness: int = 30
    lightnessPenalty: float = 0.3


class StringArtRequest(BaseModel):
    id: str
    userID: str
    image: str
    deviceID: str=''
    specifications: ArtSpecifiactions


class ArtProgressRequest(BaseModel):
    id: str = ''
    artID: str  # This field is required
    threads: List[int] = []
    iteration: int = 0
    status: str
    message: str
    progress: float = 0.0



class ArtRequest(BaseModel):
    image: str
    canvaSize: int = 512
    margin: int = 20
    nailCount: int = 200
    threadCount: int = 3500
    lineDarkness: int = 30
    lightnessPenalty: float = 0.3
    backGroundEnabled: bool = False


class ArtStatus(BaseModel):
    threads: List[int] = []
    iteration: int = 0
    status: str = "pending"
    message: str = "Art generation queued"
    progress: float = 0.0
    
class ArtResponse(BaseModel):
    threadCount: int
    threadIndex: List[int]
    nailCount: int
    nailIndex: List
    image: str
    