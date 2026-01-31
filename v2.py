import base64
import time
import io
import os
import struct
import numpy as np
import math
from PIL import Image
import cv2
import requests

from firebase_service import FirebaseService
from models.device_model import ArtResponse, ArtStatus

class StringArtProcessor:
    def __init__(self, artID):
        self.firebaseService = FirebaseService()
        self.artID = artID
        self.data = self.firebaseService.getArtRequest(artID)
        
        self.Nails = []
        self.ThreadIndex = []
        self.DISPLAY = None
        self.IMG = None
        
        # Pre-calculated Line Data
        # Using a list of lists for O(1) access during the hot loop
        self.line_coords = [] 
        
        self.firebaseService.updateResponce({
            'threadCount': 0,
            'progress': 0,
            'threads': [],
            'message': 'Getting Started',
            'status': 'init'
        })

    def downloadImage(self):
        try:
            image_url = self.data.image
            self.firebaseService.updateResponce({
                'message': 'Downloading Image',
                'status': 'downloadImage'
            })
            
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            return Image.open(io.BytesIO(response.content))
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

        # IMG is target (255 is dark, 0 is light)
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
            # Clip nail positions to be within image boundaries
            x = max(0, min(x, self.data.canvaSize - 1))
            y = max(0, min(y, self.data.canvaSize - 1))
            self.Nails.append((x, y))

    def precompute_all_lines(self):
        """Precompute all possible line coordinates to maximize loop speed"""
        self.firebaseService.updateResponce({
            'message': 'Precomputing all possible lines...',
            'status': 'Precompute'
        })
        n = self.data.nailCount
        # We store as self.line_coords[start_nail][end_nail]
        self.line_coords = [{} for _ in range(n)]
        
        for i in range(n):
            p1 = self.Nails[i]
            for j in range(i + 1, n):
                # Skip neighbors
                if min(abs(i - j), n - abs(i - j)) < 10:
                    continue
                
                p2 = self.Nails[j]
                y_idx, x_idx = self.get_line_pixels_vectorized(p1, p2)
                
                coords = (y_idx, x_idx)
                self.line_coords[i][j] = coords
                self.line_coords[j][i] = coords

    def get_line_pixels_vectorized(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx, sy = (1 if x1 < x2 else -1), (1 if y1 < y2 else -1)
        err = dx - dy
        x, y = x1, y1
        xs, ys = [], []
        
        # Max index allowed is canvaSize - 1
        limit = self.data.canvaSize - 1
        
        while True:
            # Add safety clipping for coordinates
            xs.append(max(0, min(x, limit)))
            ys.append(max(0, min(y, limit)))
            if x == x2 and y == y2: break
            e2 = 2 * err
            if e2 > -dy: err -= dy; x += sx
            if e2 < dx: err += dx; y += sy
            
        return np.array(ys, dtype=np.int32), np.array(xs, dtype=np.int32)

    def genaratePath(self):
        """Generate portrait string art using precomputed lines and vectorized penalty"""
        self.precompute_all_lines()
        
        self.firebaseService.updateResponce({
            'message': 'Generating Thread Path',
            'status': 'generatePath'
        })


        
        current_nail = 0
        self.ThreadIndex = [current_nail]
        
        # Local variables for faster access
        img = self.IMG
        display = self.DISPLAY
        line_darkness = self.data.lineDarkness
        l_penalty = self.data.lightnessPenalty
        
        for iteration in range(1, self.data.threadCount):
            best_reduction = -1e9
            next_nail = -1
            
            # Get possible lines for current nail
            possible_targets = self.line_coords[current_nail]
            
            for target_nail, (y_idx, x_idx) in possible_targets.items():
                t_vals = img[y_idx, x_idx]
                d_vals = display[y_idx, x_idx]
                
                err_before = t_vals - d_vals
                p_before = np.sum(np.maximum(0, err_before) + l_penalty * np.abs(np.minimum(0, err_before)))
                
                err_after = err_before - line_darkness
                p_after = np.sum(np.maximum(0, err_after) + l_penalty * np.abs(np.minimum(0, err_after)))
                
                reduction = (p_before - p_after) / len(y_idx)
                
                if reduction > best_reduction:
                    best_reduction = reduction
                    next_nail = target_nail
            
            if next_nail == -1 or best_reduction <= 0:
                break
                
            # Execute move
            self.ThreadIndex.append(next_nail)
            y_up, x_up = self.line_coords[current_nail][next_nail]
            display[y_up, x_up] = np.minimum(255, display[y_up, x_up] + line_darkness)
            current_nail = next_nail
            
            # Update every 50 threads
            if iteration % 50 == 0:
                progress = (iteration / self.data.threadCount) * 100
                self.firebaseService.updateResponce({
                    'message': f'Generating Threads',
                    'status': 'generatePath',
                    'threadCount': iteration,
                    'threads': self.ThreadIndex[-50:], 
                    'progress': progress
                })
                
            if iteration % 1000 == 0: # Keeping the Server Alive
                url = "https://genaratestringart.onrender.com"
                try:
                    requests.get(url, timeout=5)
                except:
                    pass

        # Final update
        self.firebaseService.updateResponce({
            'message': f'Path Generation Completed',
            'status': 'completed',
            'threadCount': len(self.ThreadIndex),
            'threads': [],
            'progress': 100.0
        })

        return len(self.ThreadIndex)

    def process(self):
        try:
            start_time = time.time()

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

            end_time = time.time()
            total_duration = round(end_time - start_time, 2)


            
            # Formatting thread index as requested
            s = ''.join(f'{v:03d}' for v in self.ThreadIndex)


            
            self.firebaseService.updateFinalResponse({
                'nailCount': self.data.nailCount,
                'threadCount': len(self.ThreadIndex),
                'totalThreads': s,
                'timeToComplete': f"{total_duration}s"
            })
            
            print(f"Completed : ->{self.artID} in {total_duration}s")
            return "Completed"
        except Exception as e:
            print(f"Processing error: {e}")
            self.firebaseService.updateResponce({
                'message': f'Error: {str(e)}',
                'status': 'Failed'
            })
            raise