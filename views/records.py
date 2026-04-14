import customtkinter as ctk

from database import SessionLocal
from models import Student


class RecordsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        # ── Search / filter row ──────────────────────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", pady=10)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh())

        ctk.CTkEntry(
            search_frame,
            textvariable=self._search_var,
            placeholder_text="Search by name or ID…",
            width=400,
        ).pack(side="left", padx=(0, 10))

        self._class_filter = ctk.CTkOptionMenu(
            search_frame,
            values=["All Classes"],
            command=lambda _: self._refresh(),
        )
        self._class_filter.pack(side="left")

        ctk.CTkButton(search_frame, text="Refresh", command=self._load_classes).pack(
            side="left", padx=10
        )

        # ── Table header ─────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, height=40, fg_color="gray20")
        header.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(
            header, text="ID  |  NAME  |  CLASS  |  STATUS", font=("Arial", 12, "bold")
        ).pack(pady=5)

        # ── Scrollable list ──────────────────────────────────────────────────
        self._list_frame = ctk.CTkScrollableFrame(self)
        self._list_frame.pack(expand=True, fill="both", pady=5)

        self._load_classes()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_classes(self) -> None:
        db = SessionLocal()
        try:
            rows = db.query(Student.class_name).distinct().all()
        finally:
            db.close()

        classes = ["All Classes"] + sorted({r[0] for r in rows if r[0]})
        self._class_filter.configure(values=classes)
        self._refresh()

    def _refresh(self) -> None:
        query_text = self._search_var.get().strip().lower()
        class_filter = self._class_filter.get()

        db = SessionLocal()
        try:
            q = db.query(Student)
            if class_filter != "All Classes":
                q = q.filter(Student.class_name == class_filter)
            students = q.order_by(Student.id).limit(200).all()
        finally:
            db.close()

        # Filter by search text client-side (already limited to 200 rows)
        if query_text:
            students = [
                s for s in students
                if query_text in s.full_name.lower() or query_text in str(s.id)
            ]

        # Rebuild list
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        if not students:
            ctk.CTkLabel(self._list_frame, text="No students found.").pack(pady=20)
            return

        for student in students:
            status = "Active" if student.is_active else "Inactive"
            row_text = f"{student.id}  |  {student.full_name}  |  {student.class_name or '—'}  |  {status}"
            ctk.CTkLabel(self._list_frame, text=row_text, anchor="w").pack(
                fill="x", pady=2, padx=10
            )
