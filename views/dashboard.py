import customtkinter as ctk
from sqlalchemy import func

from database import SessionLocal
from models import Event, Student


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        ctk.CTkLabel(self, text="School Overview", font=("Arial", 32, "bold")).pack(
            pady=(0, 20), anchor="w"
        )

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", pady=10)

        self._total_val = self._make_card(cards_frame, "TOTAL STUDENTS", "#3498db", 0)
        self._inside_val = self._make_card(cards_frame, "INSIDE NOW", "#2ecc71", 1)
        self._unknown_val = self._make_card(cards_frame, "UNKNOWN TODAY", "#e74c3c", 2)

        ctk.CTkButton(self, text="Refresh", command=self.load_data).pack(
            anchor="w", padx=5, pady=10
        )

        self.load_data()

    def _make_card(self, parent: ctk.CTkFrame, title: str, color: str, col: int) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, width=200, height=120, corner_radius=15)
        card.grid(row=0, column=col, padx=10)
        card.grid_propagate(False)

        ctk.CTkLabel(card, text=title, font=("Arial", 12, "bold"), text_color="gray").pack(
            pady=(15, 0)
        )
        val_label = ctk.CTkLabel(card, text="—", font=("Arial", 36, "bold"), text_color=color)
        val_label.pack(pady=10)
        return val_label

    def load_data(self) -> None:
        db = SessionLocal()
        try:
            total = (
                db.query(func.count(Student.id)).filter(Student.is_active.is_(True)).scalar() or 0
            )
            inside = (
                db.query(func.count(Event.id))
                .filter(Event.event_type == "IN", Event.is_unknown.is_(False))
                .scalar()
                or 0
            )
            unknown_today = (
                db.query(func.count(Event.id)).filter(Event.is_unknown.is_(True)).scalar() or 0
            )
        finally:
            db.close()

        self._total_val.configure(text=str(total))
        self._inside_val.configure(text=str(inside))
        self._unknown_val.configure(text=str(unknown_today))
