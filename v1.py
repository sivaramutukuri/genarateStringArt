# =========================
# Imports
# =========================
from flask import jsonify
import cv2
import numpy as np
import math
from PIL import Image
import io
import requests
import threading

from firebase import FirestoreManager, StorageManager


# =========================
# Default Configuration
# =========================
DEFAULT_CANVAS_SIZE = 512
DEFAULT_MARGIN = 20
DEFAULT_NAIL_COUNT = 200
DEFAULT_THREADS = 3500
DEFAULT_LINE_DARKNESS = 30
DEFAULT_LIGHTNESS_PENALTY = 0.3


# =========================
# String Art Processor
# =========================
class StringArtProcessor:
    def __init__(self, art_id: str):
        self.art_id = art_id

        # Load art config
        art = FirestoreManager.get_art(art_id)
        if not art:
            raise Exception("Art document not found")

        # Config (ALL stored on self)
        self.canvas_size = art.get("canvasSize", DEFAULT_CANVAS_SIZE)
        self.margin = art.get("margin", DEFAULT_MARGIN)
        self.nail_count = art.get("nailCount", DEFAULT_NAIL_COUNT)
        self.max_threads = art.get("portraitThreads", DEFAULT_THREADS)
        self.line_darkness = art.get("lineDarkness", DEFAULT_LINE_DARKNESS)
        self.lightness_penalty = art.get("lightnessPenalty", DEFAULT_LIGHTNESS_PENALTY)
        self.image_url = art.get("imageUrl")

        # Runtime data
        self.img = None
        self.display = None
        self.nails = []
        self.thread_index = []


    # =========================
    # Image Handling
    # =========================
    def download_image(self):
        response = requests.get(self.image_url, timeout=10)
        if response.status_code != 200:
            raise Exception("Failed to download image")

        return Image.open(io.BytesIO(response.content))


    def convert_image(self, image: Image.Image):
        image = image.convert("L")
        image = image.resize((self.canvas_size, self.canvas_size))

        self.img = 255 - np.asarray(image, dtype=np.float32)
        self.display = np.zeros_like(self.img)


    # =========================
    # Geometry
    # =========================
    def generate_nails(self):
        self.nails.clear()
        center = self.canvas_size // 2
        radius = center - self.margin

        for i in range(self.nail_count):
            angle = 2 * math.pi * i / self.nail_count
            x = int(center + radius * math.cos(angle))
            y = int(center + radius * math.sin(angle))
            self.nails.append((x, y))


    def get_line_pixels(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2

        pixels = []
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx, sy = (1, 1) if x1 < x2 else (-1, -1)
        err = dx - dy

        x, y = x1, y1
        while True:
            if 0 <= x < self.canvas_size and 0 <= y < self.canvas_size:
                pixels.append((y, x))
            if x == x2 and y == y2:
                break
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

        return pixels


    # =========================
    # Scoring
    # =========================
    def calculate_penalty(self, pixels):
        penalty = 0
        for y, x in pixels:
            diff = self.img[y, x] - self.display[y, x]
            penalty += diff if diff >= 0 else self.lightness_penalty * abs(diff)
        return penalty


    def penalty_reduction(self, p1, p2):
        pixels = self.get_line_pixels(p1, p2)
        if not pixels:
            return 0

        before = self.calculate_penalty(pixels)
        after = 0

        for y, x in pixels:
            new_val = self.display[y, x] + self.line_darkness
            diff = self.img[y, x] - new_val
            after += diff if diff >= 0 else self.lightness_penalty * abs(diff)

        return (before - after) / len(pixels)


    def apply_line(self, p1, p2):
        for y, x in self.get_line_pixels(p1, p2):
            self.display[y, x] = min(255, self.display[y, x] + self.line_darkness)


    # =========================
    # Main Algorithm
    # =========================
    def find_next_nail(self, current):
        best_score = -1
        best_index = -1

        for i in range(self.nail_count):
            if i == current:
                continue
            dist = min(abs(i - current), self.nail_count - abs(i - current))
            if dist < 3:
                continue

            score = self.penalty_reduction(self.nails[current], self.nails[i])
            if score > best_score:
                best_score = score
                best_index = i

        return best_index, best_score


    def generate_threads(self):
        FirestoreManager.update_status(self.art_id, "processing", "Generating threads")

        current = 0
        self.thread_index = [current]

        for i in range(1, self.max_threads):
            nxt, score = self.find_next_nail(current)
            if nxt == -1 or score <= 0:
                break

            self.apply_line(self.nails[current], self.nails[nxt])
            self.thread_index.append(nxt)
            current = nxt

            if i % 50 == 0:
                FirestoreManager.update_progress(
                    self.art_id,
                    (i / self.max_threads) * 100,
                    i,
                    score,
                    i
                )
                FirestoreManager.create_thread_batch(
                    self.art_id, i, self.thread_index[-50:]
                )

        return len(self.thread_index)


    # =========================
    # Rendering
    # =========================
    def render_final(self):
        canvas = np.ones((self.canvas_size, self.canvas_size, 3), np.uint8) * 255

        for i in range(1, len(self.thread_index)):
            cv2.line(
                canvas,
                self.nails[self.thread_index[i - 1]],
                self.nails[self.thread_index[i]],
                (0, 0, 0),
                1,
                cv2.LINE_AA
            )

        return canvas


    # =========================
    # Orchestration
    # =========================
    def process(self):
        image = self.download_image()
        self.convert_image(image)
        self.generate_nails()
        total = self.generate_threads()

        final = self.render_final()
        url = StorageManager.upload_image_from_array(self.art_id, final)

        FirestoreManager.save_all_threads(self.art_id, self.thread_index)
        FirestoreManager.mark_completed(self.art_id, url, total)

        return url, total


# =========================
# Background Worker
# =========================
def process_art_async(art_id):
    processor = StringArtProcessor(art_id)
    processor.process()


# =========================
# Flask Entry
# =========================
def startGenarate(art_id):
    if not art_id:
        return jsonify({"error": "art_id required"}), 400

    art = FirestoreManager.get_art(art_id)
    if not art:
        return jsonify({"error": "Art not found"}), 404

    thread = threading.Thread(target=process_art_async, args=(art_id,), daemon=True)
    thread.start()

    return jsonify({
        "success": True,
        "art_id": art_id,
        "message": "Processing started"
    }), 202
