# processer.py
import base64
import io
import os
import numpy as np
import math
from PIL import Image
import cv2
import requests
# import requests  # Fixed import

from firebase_service import FirebaseService
from models.device_model import  ArtResponse, ArtStatus
# from supabase_manager import SupabaseService


# supabaseService = SupabaseService()


class StringArtProcessor:
    def __init__(self, artID):
        self.firebaseService = FirebaseService()
        self.artID = artID
        self.data = self.firebaseService.getArtRequest(artID)
    
        
        self.Nails = []
        self.ThreadIndex = []
        self.DISPLAY = None
        self.IMG = None
        

    def downloadImage(self):
        try:

            image_url =  self.data.image
            
            self.firebaseService.updateResponce({
                'message': 'Downloading Image',
                'status': 'downloadImage'
            })
            
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            image = Image.open(io.BytesIO(response.content))
            return image
        except Exception as e:
            raise Exception(f"Error Extracting Bytes {e}")

    
    def convertImage(self, image):
        """Convert image to grayscale array"""
        img = image.convert('L')
        img = img.resize((self.data.canvaSize, self.data.canvaSize))
        
        self.firebaseService.updateResponce({
            'message': 'Converting to Grayscale',
            'status': 'convertImage'
        })

        self.IMG = 255 - np.asarray(img, dtype=np.float32)
        self.DISPLAY = np.zeros((self.data.canvaSize, self.data.canvaSize), dtype=np.float32)

    def generateNails(self):
        """Generate nail positions around the circle"""
        self.Nails.clear()
        center = self.data.canvaSize // 2
        radius = center - self.data.margin
        
        self.firebaseService.updateResponce({
            'message': 'Generating Nail Positions',
            'status': 'generatingNails'
        })
        
        for i in range(self.data.nailCount):
            angle = 2 * math.pi * i / self.data.nailCount
            x = int(center + radius * math.cos(angle))
            y = int(center + radius * math.sin(angle))
            self.Nails.append((x, y))

    def genaratePath(self):
        """Generate portrait string art"""
        self.firebaseService.updateResponce({
            'message': 'Generating Thread Path',
            'status': 'generatePath'
        })
        
        current_index = 0
        self.ThreadIndex = [current_index]
        
        for iteration in range(1, self.data.threadCount):
            next_index, reduction = self.findNextNail(current_index)
            
            if next_index == -1 or reduction <= 0:
                break
            
            self.ThreadIndex.append(next_index)
            self.updateLine(self.Nails[current_index], self.Nails[next_index])
            current_index = next_index
            
            # Update every 50 threads
            progress = (iteration / self.data.threadCount) * 100
            if iteration % 50 == 0:
                self.firebaseService.updateResponce({
                    'message': f'Generating Threads  remaining)',
                    'status': 'generatePath',
                    'threadCount': iteration,
                    'threads': self.ThreadIndex[-50:], 
                    'progress': progress
                })
            if iteration % 1000 == 0: # Keeping the Server Alive
                url = "https://genaratestringart.onrender.com"
                requests.get(url)
                

        # Final update
        self.firebaseService.updateResponce({
            'message': f'Path Generation Completed in s',
            'status': 'completed',
            'threadCount': len(self.ThreadIndex),
            'threads': [],
            'progress': 100.0
        })

        return len(self.ThreadIndex)
    
    def findNextNail(self, current_index):
        max_reduction = -float('inf')
        next_index = -1
        
        for i in range(len(self.Nails)):
            if i == current_index:
                continue
            
            dist = min(abs(i - current_index), self.data.nailCount - abs(i - current_index))
            if dist < 3:
                continue
            
            reduction = self.calculatePenaltyReduction(self.Nails[current_index], self.Nails[i])
            
            if reduction > max_reduction:
                max_reduction = reduction
                next_index = i
        
        return next_index, max_reduction
    

    def calculatePenaltyReduction(self, p1, p2):
        """Calculate how much this line reduces the penalty"""
        pixels = self.getLinePixels(p1, p2)
        if not pixels:
            return 0
        
        current_penalty = self.calculatePenalty(pixels)
        
        penalty_after = 0
        for y, x in pixels:
            new_value = self.DISPLAY[y, x] + self.data.lineDarkness
            diff = self.IMG[y, x] - new_value
            
            if diff >= 0:
                penalty_after += diff
            else:
                penalty_after += self.data.lightnessPenalty * abs(diff)
        
        penalty_reduction = current_penalty - penalty_after
        return penalty_reduction / len(pixels)
    
    
    def getLinePixels(self, p1, p2):
        """Get all pixels along a line using Bresenham"""
        x1, y1 = p1
        x2, y2 = p2
        
        pixels = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while True:
            if 0 <= x < self.data.canvaSize and 0 <= y < self.data.canvaSize:
                pixels.append((y, x))
            
            if x == x2 and y == y2:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return pixels
    
    def calculatePenalty(self, pixels):
        """Calculate current penalty for given pixels"""
        penalty = 0
        for y, x in pixels:
            diff = self.IMG[y, x] - self.DISPLAY[y, x]
            
            if diff >= 0:
                penalty += diff
            else:
                penalty += self.data.lightnessPenalty * abs(diff)
        
        return penalty
    
    def updateLine(self, p1, p2):
        """Add darkness along the line"""
        pixels = self.getLinePixels(p1, p2)
        
        for y, x in pixels:
            self.DISPLAY[y, x] = min(255, self.DISPLAY[y, x] + self.data.lineDarkness)

    

    def process(self):
        try:

            self.firebaseService.updateResponce({
                    'threadCount': 0,
                    'progress': 0,
                    'threads': [],
                    'message': 'Getting Started',
                    'status': 'init'
                })
            image = self.downloadImage()
            self.convertImage(image)
            self.generateNails()
            self.genaratePath()

            byte_data = bytes(self.ThreadIndex)

            base64_str = base64.b64encode(byte_data).decode("utf-8")


            self.firebaseService.updateFinalResponse({
                'nailCount':self.data.nailCount,
                'threadCount': len(self.ThreadIndex),
                'totalThreads': base64_str,
            })
            print(f"Completed : ->{self.artID}")
            return "Completed"
          
        except Exception as e:
            print(f"Processing error: {e}")
            self.firebaseService.updateResponce(
                 ArtStatus(
                    message=f'Error: {str(e)}',
                    status='Failed'
                )
            )
            raise


# import io
# import os
# import numpy as np
# import math
# from PIL import Image
# import cv2

# from fastapi import requests
# from models.device_model import ArtProgressRequest
# from supabase_manager import SupabaseService


# supabaseService = SupabaseService()


# class StringArtProcessor:
#         def __init__(self, artID):
#             self.data = supabaseService.getArt(artID)
#             self.Nails = []
#             self.ThreadIndex = []
#             self.DISPLAY = None
#             self.IMG = None
#             self.sp = self.data.specifications
#             supabaseService.createThread(ArtProgressRequest(message='Getting Started',status='Init'))
            

#         def downloadImage(self):
#             IMAGEBACKET = os.getenv("IMAGEBACKET")
#             response = requests.get(IMAGEBACKET + self.data.image, timeout=10)
#             supabaseService.createThread(ArtProgressRequest(message='Extrating Image',status='downloadImage'))
            
#             if response.status_code == 200:
#                 image = Image.open(io.BytesIO(response.content))
#                 return image
#             else:
#                 raise Exception(f"Failed to download image: {response.status_code}")
        
#         def convertImage(self, image):
#             """Convert image to grayscale array"""
#             img = image.convert('L')
#             img = img.resize((self.canvaSize, self.canvaSize))
#             supabaseService.createThread(ArtProgressRequest(message='Converting Into GreyScale Image',status='convertImage'))

#             self.IMG = 255 - np.asarray(img, dtype=np.float32)
#             self.DISPLAY = np.zeros((self.canvaSize, self.canvaSize), dtype=np.float32)

#         def generateNails(self):
#             """Generate nail positions around the circle"""
#             self.Nails.clear()
#             center = self.canvaSize // 2
#             radius = center - self.margin
#             supabaseService.createThread(ArtProgressRequest(message='Generate nail positions around the circle',status='GenaratingNails'))

            
#             for i in range(self.nailCount):
#                 angle = 2 * math.pi * i / self.nailCount
#                 x = int(center + radius * math.cos(angle))
#                 y = int(center + radius * math.sin(angle))
#                 self.Nails.append((x, y))

#         def genaratePath(self):
#             """Generate portrait string art"""
#             supabaseService.createThread(ArtProgressRequest(message='Generating Threads',status='genaratePath'))

            
#             current_index = 0
#             self.ThreadIndex = [current_index]
            
#             for iteration in range(1, self.threadCount):
#                 next_index, reduction = self.findNextNail(current_index)
                
#                 if next_index == -1 or reduction <= 0:
#                     break
                
#                 self.ThreadIndex.append(next_index)
#                 self.updateLine(self.Nails[current_index], self.Nails[next_index])
#                 current_index = next_index
                
#                 # Update Firestore every 50 threads
#                 progress = (iteration / self.threadCount) * 100
#                 if iteration % 50 == 0:
#                     supabaseService.createThread(ArtProgressRequest(message='Generating Threads',status='genaratePath',count=iteration,threads=self.ThreadIndex,progress=progress,))
#                 else :
#                     supabaseService.createThread(ArtProgressRequest(message='Process Completed',status='genaratePath',count=iteration,threads=self.ThreadIndex,progress=100,))

#             # supabaseService.completeArt()

#             return len(self.ThreadIndex)
        
        

#         def findNextNail(self, current_index):
#             max_reduction = -float('inf')
#             next_index = -1
            
#             for i in range(len(self.Nails)):
#                 if i == current_index:
#                     continue
                
#                 dist = min(abs(i - current_index), self.nailCount - abs(i - current_index))
#                 if dist < 3:
#                     continue
                
#                 reduction = self.calculatePenaltyReduction(self.Nails[current_index], self.Nails[i])
                
#                 if reduction > max_reduction:
#                     max_reduction = reduction
#                     next_index = i
            
#             return next_index, max_reduction
        

#         def calculatePenaltyReduction(self, p1, p2):
#             """Calculate how much this line reduces the penalty"""
#             pixels = self.getLinePixels(p1, p2)
#             if not pixels:
#                 return 0
            
#             current_penalty = self.calculatePenalty(pixels)
            
#             penalty_after = 0
#             for y, x in pixels:
#                 new_value = self.DISPLAY[y, x] + self.lineDarkness
#                 diff = self.IMG[y, x] - new_value
                
#                 if diff >= 0:
#                     penalty_after += diff
#                 else:
#                     penalty_after += self.lightnessPenalty * abs(diff)
            
#             penalty_reduction = current_penalty - penalty_after
#             return penalty_reduction / len(pixels)
        
        
#         def getLinePixels(self, p1, p2):
#             """Get all pixels along a line using Bresenham"""
#             x1, y1 = p1
#             x2, y2 = p2
            
#             pixels = []
#             dx = abs(x2 - x1)
#             dy = abs(y2 - y1)
#             sx = 1 if x1 < x2 else -1
#             sy = 1 if y1 < y2 else -1
#             err = dx - dy
            
#             x, y = x1, y1
            
#             while True:
#                 if 0 <= x < self.canvaSize and 0 <= y < self.canvaSize:
#                     pixels.append((y, x))
                
#                 if x == x2 and y == y2:
#                     break
                    
#                 e2 = 2 * err
#                 if e2 > -dy:
#                     err -= dy
#                     x += sx
#                 if e2 < dx:
#                     err += dx
#                     y += sy
            
#             return pixels
#         def calculatePenalty(self, pixels):
#             """Calculate current penalty for given pixels"""
#             penalty = 0
#             for y, x in pixels:
#                 diff = self.IMG[y, x] - self.DISPLAY[y, x]
                
#                 if diff >= 0:
#                     penalty += diff
#                 else:
#                     penalty += self.lightnessPenalty * abs(diff)
            
#             return penalty
        
#         def updateLine(self, p1, p2):
#             """Add darkness along the line"""
#             pixels = self.getLinePixels(p1, p2)
            
#             for y, x in pixels:
#                 self.DISPLAY[y, x] = min(255, self.DISPLAY[y, x] + self.lineDarkness)

#         def renderFinal(self):
#             """Create final clean artwork"""
#             final_canvas = np.ones((self.canvaSize, self.canvaSize, 3), dtype=np.uint8) * 255
            
#             # Draw all threads
#             for i in range(1, len(self.ThreadIndex)):
#                 n1 = self.Nails[self.ThreadIndex[i - 1]]
#                 n2 = self.Nails[self.ThreadIndex[i]]
#                 cv2.line(final_canvas, n1, n2, (0, 0, 0), 1, cv2.LINE_AA)
            
#             # Draw nails
#             for x, y in self.Nails:
#                 cv2.circle(final_canvas, (x, y), 1, (200, 200, 200), -1)
            
#             supabaseService.createThread(ArtProgressRequest(message='Create final clean artwork',status='rendaringArtWork',count=100,threads=self.ThreadIndex,progress=100,))

            
#             success, buffer = cv2.imencode(".png", final_canvas)
#             if not success:
#                 raise ValueError("Failed to encode image")
            
#             res = supabaseService.uploadOutputImg(buffer.tobytes())

#             return res

#             # supabaseService.completeArt(data=self.ThreadIndex,total=len(self.ThreadIndex),img=res,nails= self.Nails)


#         def process(self):
#             try:
#                 image = self.downloadImage()
#                 self.convertImage(image)
#                 self.generateNails()
#                 total_threads = self.genaratePath()
#                 final_image = self.renderFinal()
#                 supabaseService.completeArt(data=self.ThreadIndex,total=len(self.ThreadIndex),img=final_image,nails= self.Nails)
#             except Exception as e:
#                 supabaseService.createThread(ArtProgressRequest(message=f'{str(e)}',status='Failed'))
#                 return None

