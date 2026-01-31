import customtkinter as ctk
from datetime import datetime
import random

class LiveFeedView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Top Bar with Title and Simulation Button
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", pady=10)

        self.label = ctk.CTkLabel(self.top_bar, text="Live Attendance Feed", font=("Arial", 24, "bold"))
        self.label.pack(side="left")

        self.test_btn = ctk.CTkButton(self.top_bar, text="Simulate Detection", command=self.simulate_detection)
        self.test_btn.pack(side="right")

        # The Scrollable Area
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Detection Log (Most Recent First)")
        self.scroll_frame.pack(expand=True, fill="both")

    def simulate_detection(self):
        """Creates a dummy card to test the visual flow"""
        names = ["John Smith", "Emma Wilson", "Ali Khan", "Maria Garcia", "Liam Chen"]
        directions = ["IN", "OUT"]
        
        name = random.choice(names)
        direction = random.choice(directions)
        time = datetime.now().strftime("%H:%M:%S")
        
        self.add_log_card(name, direction, time)

    def add_log_card(self, name, direction, time):
        color = "#2ecc71" if direction == "IN" else "#e74c3c"
        
        # Newest items should appear at the top
        card = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", height=50)
        card.pack(fill="x", pady=5, before=None) # Note: CustomTkinter packs linearly; use 'before' for ordering if needed
        
        # In a real app, you'd add a photo here
        lbl_photo = ctk.CTkLabel(card, text="👤", font=("Arial", 20))
        lbl_photo.pack(side="left", padx=15)

        lbl_info = ctk.CTkLabel(card, text=f"{name} marked as {direction} at {time}", font=("Arial", 14))
        lbl_info.pack(side="left", padx=10)
        
        lbl_status = ctk.CTkLabel(card, text=direction, text_color=color, font=("Arial", 12, "bold"))
        lbl_status.pack(side="right", padx=20)