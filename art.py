from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import math
from PIL import Image
import io
import base64
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import  firestore
import threading
import uuid
from firebase import FirestoreManager, StorageManager





# String Art Parameters
CANVAS_SIZE = 512
MARGIN = 20
NailCount = 200
PORTRAIT_THREADS = 3500
LINE_DARKNESS = 30
LIGHTNESS_PENALTY = 0.3
ImageUrl = ""


class StringArtProcessor:
    def __init__(self, art_id: str):
        data =  FirestoreManager.get_art(art_id)
        CANVAS_SIZE = data.get('canvasSize', CANVAS_SIZE)
        MARGIN = data.get('margin', MARGIN)
        NailCount = data.get('nailCount', NailCount)
        PORTRAIT_THREADS = data.get('portraitThreads', PORTRAIT_THREADS)
        LINE_DARKNESS = data.get('lineDarkness', LINE_DARKNESS)
        LIGHTNESS_PENALTY = data.get('lightnessPenalty', LIGHTNESS_PENALTY)
        ImageUrl = data.get('imageUrl', "")
        self.art_id = art_id
        self.DISPLAY = None
        self.IMG = None
        self.Nails = []
        self.ThreadIndex = []
        
    def download_image(self):
        """Download image from URL"""
        response = requests.get(ImageUrl, timeout=10)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            return image
        else:
            raise Exception(f"Failed to download image: {response.status_code}")
    
    def convertImage(self, image):
        """Convert image to grayscale array"""
        img = image.convert('L')
        img = img.resize((CANVAS_SIZE, CANVAS_SIZE))
        
        self.IMG = 255 - np.asarray(img, dtype=np.float32)
        self.DISPLAY = np.zeros((CANVAS_SIZE, CANVAS_SIZE), dtype=np.float32)
    
    def generateNails(self):
        """Generate nail positions around the circle"""
        self.Nails.clear()
        center = CANVAS_SIZE // 2
        radius = center - MARGIN
        
        for i in range(NailCount):
            angle = 2 * math.pi * i / NailCount
            x = int(center + radius * math.cos(angle))
            y = int(center + radius * math.sin(angle))
            self.Nails.append((x, y))
    
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
            if 0 <= x < CANVAS_SIZE and 0 <= y < CANVAS_SIZE:
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
                penalty += LIGHTNESS_PENALTY * abs(diff)
        
        return penalty
    
    def calculatePenaltyReduction(self, p1, p2):
        """Calculate how much this line reduces the penalty"""
        pixels = self.getLinePixels(p1, p2)
        if not pixels:
            return 0
        
        current_penalty = self.calculatePenalty(pixels)
        
        penalty_after = 0
        for y, x in pixels:
            new_value = self.DISPLAY[y, x] + LINE_DARKNESS
            diff = self.IMG[y, x] - new_value
            
            if diff >= 0:
                penalty_after += diff
            else:
                penalty_after += LIGHTNESS_PENALTY * abs(diff)
        
        penalty_reduction = current_penalty - penalty_after
        return penalty_reduction / len(pixels)
    
    def updateLine(self, p1, p2):
        """Add darkness along the line"""
        pixels = self.getLinePixels(p1, p2)
        
        for y, x in pixels:
            self.DISPLAY[y, x] = min(255, self.DISPLAY[y, x] + LINE_DARKNESS)
    
    def findNextNail(self, current_index):
        """Find the nail that gives maximum penalty reduction"""
        max_reduction = -float('inf')
        next_index = -1
        
        for i in range(len(self.Nails)):
            if i == current_index:
                continue
            
            dist = min(abs(i - current_index), NailCount - abs(i - current_index))
            if dist < 3:
                continue
            
            reduction = self.calculatePenaltyReduction(self.Nails[current_index], self.Nails[i])
            
            if reduction > max_reduction:
                max_reduction = reduction
                next_index = i
        
        return next_index, max_reduction
    
    def findPortraitPath(self):
        """Generate portrait string art"""
        FirestoreManager.update_status(
            art_id=self.art_id,
            status='processing',
            message='Generating string art...'
        )
        
        current_index = 0
        self.ThreadIndex = [current_index]
        
        for iteration in range(1, PORTRAIT_THREADS):
            next_index, reduction = self.findNextNail(current_index)
            
            if next_index == -1 or reduction <= 0:
                break
            
            self.ThreadIndex.append(next_index)
            self.updateLine(self.Nails[current_index], self.Nails[next_index])
            current_index = next_index
            
            # Update Firestore every 50 threads
            if iteration % 50 == 0:
                progress = (iteration / PORTRAIT_THREADS) * 100
                
                # Update progress
                FirestoreManager.update_progress(
                    art_id=self.art_id,
                    progress=progress,
                    threads_completed=iteration,
                    reduction=reduction,
                    currentIteration=iteration
                )
                
                # Save thread batch
                FirestoreManager.create_thread_batch(
                    art_id=self.art_id,
                    iteration=iteration,
                    threads=self.ThreadIndex[-50:]  # Last 50 threads
                )
        
        return len(self.ThreadIndex)
    
    def renderFinal(self):
        """Create final clean artwork"""
        final_canvas = np.ones((CANVAS_SIZE, CANVAS_SIZE, 3), dtype=np.uint8) * 255
        
        # Draw all threads
        for i in range(1, len(self.ThreadIndex)):
            n1 = self.Nails[self.ThreadIndex[i - 1]]
            n2 = self.Nails[self.ThreadIndex[i]]
            cv2.line(final_canvas, n1, n2, (0, 0, 0), 1, cv2.LINE_AA)
        
        # Draw nails
        for x, y in self.Nails:
            cv2.circle(final_canvas, (x, y), 1, (200, 200, 200), -1)
        
        return final_canvas
    
    def process(self, image_url: str):
        """Main processing function"""
        try:
            # Update status: downloading
            FirestoreManager.update_status(
                art_id=self.art_id,
                status='downloading',
                message='Downloading image...'
            )
            image = self.download_image(image_url)
            
            # Update status: converting
            FirestoreManager.update_status(
                art_id=self.art_id,
                status='converting',
                message='Converting image...'
            )
            self.convertImage(image)
            
            # Update status: preparing
            FirestoreManager.update_status(
                art_id=self.art_id,
                status='preparing',
                message='Generating nails...'
            )
            self.generateNails()
            
            # Generate portrait
            total_threads = self.findPortraitPath()
            
            # Render final
            FirestoreManager.update_status(
                art_id=self.art_id,
                status='rendering',
                message='Rendering final image...'
            )
            final_image = self.renderFinal()
            
            # Upload to Firebase
            FirestoreManager.update_status(
                art_id=self.art_id,
                status='uploading',
                message='Uploading to Firebase...'
            )
            output_url = StorageManager.upload_image_from_array(
                art_id=self.art_id,
                image_array=final_image
            )
            
            # Save all threads
            FirestoreManager.save_all_threads(
                art_id=self.art_id,
                threads=self.ThreadIndex
            )
            
            # Mark as completed
            FirestoreManager.mark_completed(
                art_id=self.art_id,
                output_url=output_url,
                total_threads=total_threads
            )
            
            return {
                'success': True,
                'output_url': output_url,
                'total_threads': total_threads
            }
            
        except Exception as e:
            # Mark as failed
            FirestoreManager.mark_failed(
                art_id=self.art_id,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'error': str(e)
            }


def process_art_async(art_id: str, image_url: str):
    """Process art in background thread"""
    processor = StringArtProcessor(art_id)
    processor.process(image_url)


def process_art(art_id: str):
    
    try:
        art_data = FirestoreManager.get_art(art_id)
        if not art_id:
            return jsonify({'error': 'art_id is required'}), 400
        

        image_url = art_data['imageUrl'] 
        
        
        if not image_url:
            return jsonify({'error': 'image_url is required'}), 400
        
        # Check if art exists
        if not art_data:
            return jsonify({'error': 'Art document not found'}), 404
        
        # Start processing in background
        thread = threading.Thread(
            target=process_art_async,
            args=(art_id, image_url)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'art_id': art_id,
            'message': 'Processing started. Check Firestore for updates.'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
