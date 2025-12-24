import cv2
import numpy as np
import math
import requests
import io
from PIL import Image
from firebase_manager import FirebaseManager

class StringArtProcessor:
    def __init__(self, art_id: str, fm: FirebaseManager):
        self.fm = fm
        self.art_id = art_id
        
        art = fm.get_art(art_id)
        if not art: raise ValueError("Art not found")

        self.canvas_size = art.get("canvasSize", 512)
        self.nail_count = art.get("nailCount", 200)
        self.max_threads = art.get("portraitThreads", 3500)
        self.line_darkness = art.get("lineDarkness", 30)
        self.lightness_penalty = art.get("lightnessPenalty", 0.3)
        self.image_url = art.get("imageUrl")
        
        self.nails = self._generate_nails()

    def _generate_nails(self):
        center = self.canvas_size // 2
        radius = center - 20
        nails = []
        for i in range(self.nail_count):
            angle = 2 * math.pi * i / self.nail_count
            nails.append((
                int(center + radius * math.cos(angle)),
                int(center + radius * math.sin(angle))
            ))
        return nails

    def _get_line_pixels(self, p1, p2):
        # Fast Bresenham's implementation
        x1, y1 = p1
        x2, y2 = p2
        dx, dy = abs(x2-x1), abs(y2-y1)
        steep = dy > dx
        if steep: x1, y1, x2, y2 = y1, x1, y2, x2
        if x1 > x2: x1, x2, y1, y2 = x2, x1, y2, y1
        
        dx, dy = x2-x1, abs(y2-y1)
        error = dx // 2
        ystep = 1 if y1 < y2 else -1
        y = y1
        
        pixels = []
        for x in range(x1, x2 + 1):
            pixels.append((x, y) if steep else (y, x))
            error -= dy
            if error < 0:
                y += ystep
                error += dx
        return np.array(pixels)

    def process(self):
        try:
            # 1. Prepare Image
            resp = requests.get(self.image_url, timeout=10)
            img_pil = Image.open(io.BytesIO(resp.content)).convert("L").resize((self.canvas_size, self.canvas_size))
            target = 255 - np.asarray(img_pil, dtype=np.float32)
            canvas = np.zeros_like(target)

            # 2. Iterative Threading
            current_nail = 0
            thread_indices = [current_nail]
            
            self.fm.update_status(self.art_id, "processing", message="Starting generation")

            for i in range(1, self.max_threads):
                best_nail, best_score = -1, -1000
                
                # Vectorized search would require pre-calculated lines, 
                # for now we optimize the scoring loop
                for n in range(self.nail_count):
                    if abs(n - current_nail) < 3: continue
                    
                    pixels = self._get_line_pixels(self.nails[current_nail], self.nails[n])
                    y, x = pixels[:, 0], pixels[:, 1]
                    
                    # Optimized scoring using NumPy indexing
                    line_vals = canvas[y, x]
                    target_vals = target[y, x]
                    
                    # Calculate score (penalty reduction)
                    diff_before = target_vals - line_vals
                    # Weighting negative differences by lightness_penalty
                    score_before = np.where(diff_before >= 0, diff_before, self.lightness_penalty * np.abs(diff_before)).sum()
                    
                    new_line_vals = line_vals + self.line_darkness
                    diff_after = target_vals - new_line_vals
                    score_after = np.where(diff_after >= 0, diff_after, self.lightness_penalty * np.abs(diff_after)).sum()
                    
                    avg_reduction = (score_before - score_after) / len(pixels)
                    
                    if avg_reduction > best_score:
                        best_score = avg_reduction
                        best_nail = n

                if best_nail == -1 or best_score <= 0: break
                
                # Apply best line
                pixels = self._get_line_pixels(self.nails[current_nail], self.nails[best_nail])
                canvas[pixels[:, 0], pixels[:, 1]] = np.clip(canvas[pixels[:, 0], pixels[:, 1]] + self.line_darkness, 0, 255)
                
                thread_indices.append(best_nail)
                current_nail = best_nail

                if i % 100 == 0:
                    self.fm.update_status(self.art_id, "processing", progress=(i/self.max_threads)*100)
                    self.fm.create_thread_batch(self.art_id, i, thread_indices[-100:])

            # 3. Final Render and Upload
            final_img = np.ones((self.canvas_size, self.canvas_size, 3), np.uint8) * 255
            for idx in range(1, len(thread_indices)):
                cv2.line(final_img, self.nails[thread_indices[idx-1]], self.nails[thread_indices[idx]], (0,0,0), 1, cv2.LINE_AA)
            
            url = self.fm.upload_image(self.art_id, final_img)
            self.fm.mark_completed(self.art_id, url, len(thread_indices), thread_indices)

        except Exception as e:
            self.fm.update_status(self.art_id, "failed", error=str(e))
            print(f"Error processing {self.art_id}: {e}")