import customtkinter as ctk
from views.dashboard import DashboardView
from views.live_feed import LiveFeedView
from views.records import RecordsView

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("School Vision - Al Xorazmiy")
        self.geometry("1100x700")

        # Layout: Sidebar on left, Content on right
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.title_label = ctk.CTkLabel(self.sidebar, text="SCHOOL VISION - Al Xorazmiy", font=("Arial", 20, "bold"))
        self.title_label.pack(pady=30)

        self.btn_dash = ctk.CTkButton(self.sidebar, text="Dashboard", command=lambda: self.show_view("dash"))
        self.btn_dash.pack(pady=10, padx=20)

        self.btn_live = ctk.CTkButton(self.sidebar, text="Live Feed", command=lambda: self.show_view("live"))
        self.btn_live.pack(pady=10, padx=20)

        self.btn_rec = ctk.CTkButton(self.sidebar, text="Student Records", command=lambda: self.show_view("rec"))
        self.btn_rec.pack(pady=10, padx=20)

        # --- View Container ---
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Initialize Views
        self.views = {
            "dash": DashboardView(self.container),
            "live": LiveFeedView(self.container),
            "rec": RecordsView(self.container)
        }
        
        self.show_view("dash") # Default view

    def show_view(self, view_key):
        for view in self.views.values():
            view.pack_forget()
        self.views[view_key].pack(expand=True, fill="both")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()