import cv2
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from pyzbar import pyzbar
import pyperclip
import time
import os

# --- LOGIC ---
STORAGE_FILE = "scanned_codes.txt"

def extract_code(text):
    delimiters = ['/', '=', '?', '&', ' ', '_', '-']
    text = text.strip()
    current_parts = [text]
    for d in delimiters:
        new_parts = []
        for p in current_parts:
            split_p = p.split(d)
            new_parts.extend([s for s in split_p if s])
        current_parts = new_parts
    return current_parts[-1] if current_parts else text

def save_to_file(code):
    with open(STORAGE_FILE, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {code}\n")

# --- UI CLASS ---
class QRScannerApp:
    def __init__(self, window):
        self.window = window
        self.window.title("High-Speed Voucher Scanner")
        self.window.geometry("1000x600")
        
        # Main Layout: Left (Camera) | Right (List)
        self.main_frame = tk.Frame(self.window)
        self.main_frame.pack(fill="both", expand=True)
        
        # Left Panel (Camera)
        self.left_panel = tk.Frame(self.main_frame, width=640, height=480, bg="black")
        self.left_panel.pack(side="left", padx=10, pady=10, fill="both", expand=True)
        
        self.video_label = tk.Label(self.left_panel)
        self.video_label.pack()
        
        # Right Panel (History)
        self.right_panel = tk.Frame(self.main_frame, width=340)
        self.right_panel.pack(side="right", fill="y", padx=10, pady=10)
        
        tk.Label(self.right_panel, text="Scanned History", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Scrollable Area for History
        self.canvas = tk.Canvas(self.right_panel)
        self.scrollbar = ttk.Scrollbar(self.right_panel, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # State
        self.scanned_items = {} # {code: {"frame": tk.Frame, "label": tk.Label}}
        self.last_scanned = None
        self.last_scan_time = 0
        
        # Camera Setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        self.update_frame()

    def add_to_history(self, code):
        if code in self.scanned_items:
            return # Avoid duplicates in the visual list

        save_to_file(code)
        
        item_frame = tk.Frame(self.scrollable_frame, pady=2)
        item_frame.pack(fill="x", anchor="w")
        
        code_label = tk.Label(item_frame, text=code, font=("Courier", 11), width=20, anchor="w")
        code_label.pack(side="left")
        
        copy_btn = tk.Button(item_frame, text="Copy", command=lambda c=code, l=code_label: self.copy_code(c, l))
        copy_btn.pack(side="right", padx=5)
        
        self.scanned_items[code] = {"frame": item_frame, "label": code_label}
        
        # Auto-scroll to bottom
        self.canvas.yview_moveto(1.0)

    def copy_code(self, code, label):
        pyperclip.copy(code)
        # Apply strike-through effect
        current_text = label.cget("text")
        striked_text = "".join([char + '\u0336' for char in current_text])
        label.config(text=striked_text, fg="gray")
        print(f"Copied: {code}")

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # QR Detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            barcodes = pyzbar.decode(gray)
            
            for barcode in barcodes:
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                raw_text = barcode.data.decode("utf-8")
                extracted = extract_code(raw_text)
                
                # Overlay
                cv2.putText(frame, extracted, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Logic to add to UI
                now = time.time()
                if extracted != self.last_scanned or (now - self.last_scan_time > 2):
                    self.add_to_history(extracted)
                    self.last_scanned = extracted
                    self.last_scan_time = now

            # Convert OpenCV frame to Tkinter format
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            
            # Resize for display while keeping aspect ratio
            display_img = img.resize((640, 480), Image.Resampling.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=display_img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        self.window.after(10, self.update_frame)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

if __name__ == "__main__":
    root = tk.Tk()
    app = QRScannerApp(root)
    root.mainloop()
