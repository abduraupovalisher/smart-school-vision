import customtkinter as ctk

class RecordsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Search Tools
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(fill="x", pady=10)

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Search Student Name or ID...", width=400)
        self.search_entry.pack(side="left", padx=(0, 10))

        self.filter_class = ctk.CTkOptionMenu(self.search_frame, values=["All Classes", "9-A", "9-B", "10-A"])
        self.filter_class.pack(side="left")

        # The Table Header
        self.header_frame = ctk.CTkFrame(self, height=40, fg_color="gray20")
        self.header_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(self.header_frame, text="ID      |      NAME      |      CLASS      |      STATUS").pack(pady=5)

        # The List Area
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(expand=True, fill="both", pady=5)
        
        # Add some dummy rows for visual testing
        for i in range(10):
            dummy = ctk.CTkLabel(self.list_frame, text=f"2026_{i:03} | Student Name {i} | 10-A | {'Present' if i%2==0 else 'Absent'}")
            dummy.pack(pady=2, anchor="w", padx=10)