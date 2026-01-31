import customtkinter as ctk

class DashboardView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # Header
        self.header = ctk.CTkLabel(self, text="School Overview", font=("Arial", 32, "bold"))
        self.header.pack(pady=(0, 20), anchor="w")

        # Stats Container (Cards)
        self.stats_container = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_container.pack(fill="x", pady=10)

        # We'll create 3 cards: Total, Inside, Outside
        self.create_card(self.stats_container, "TOTAL STUDENTS", "2,000", "#3498db").grid(row=0, column=0, padx=10)
        self.create_card(self.stats_container, "INSIDE NOW", "1,452", "#2ecc71").grid(row=0, column=1, padx=10)
        self.create_card(self.stats_container, "LATE/ABSENT", "548", "#e74c3c").grid(row=0, column=2, padx=10)

    def create_card(self, master, title, value, color):
        card = ctk.CTkFrame(master, width=200, height=120, corner_radius=15)
        card.grid_propagate(False) # Keep fixed size
        
        lbl_title = ctk.CTkLabel(card, text=title, font=("Arial", 12, "bold"), text_color="gray")
        lbl_title.pack(pady=(15, 0))
        
        lbl_val = ctk.CTkLabel(card, text=value, font=("Arial", 36, "bold"), text_color=color)
        lbl_val.pack(pady=10)
        return card