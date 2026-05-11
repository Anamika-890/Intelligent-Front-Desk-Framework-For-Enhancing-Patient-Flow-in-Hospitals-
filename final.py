import firebase_admin
from firebase_admin import credentials, db
import datetime, os, tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# --- 1. FIREBASE SETUP ---
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://smart-reception-72f8e-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

class HelixAdmin:
    def __init__(self, root):
        self.root = root
        self.root.title("Resh Helix Pro | Full Patient Details")
        self.root.geometry("1200x800")
        
        # Static Background
        self.setup_bg()

        # Sidebar
        self.side = tk.Frame(root, bg="#0f172a", width=220)
        self.side.pack(side="left", fill="y")
        
        tk.Label(self.side, text="HELIX ADMIN", font=("Arial", 18, "bold"), fg="#0891b2", bg="#0f172a", pady=30).pack()
        
        tk.Button(self.side, text="📋 LIVE QUEUE", command=self.show_live, font=("Arial", 10, "bold"), pady=10).pack(fill="x", padx=15, pady=5)
        tk.Button(self.side, text="📂 VIEW HISTORY", command=self.show_history, font=("Arial", 10, "bold"), pady=10).pack(fill="x", padx=15, pady=5)
        tk.Button(self.side, text="💾 SAVE TO TXT", command=self.export_to_txt, bg="#0891b2", fg="white", font=("Arial", 10, "bold"), pady=10).pack(fill="x", padx=15, pady=20)

        # Main Workspace
        self.main = tk.Frame(root, bg="white")
        self.main.place(x=240, y=20, width=930, height=750)
        
        self.show_live()

    def setup_bg(self):
        if os.path.exists("bg.png"):
            img = Image.open("bg.png").resize((1200, 800), Image.Resampling.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(img)
            tk.Label(self.root, image=self.bg_photo).place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self.root.configure(bg="#1e293b")

    def clear_main(self):
        for widget in self.main.winfo_children():
            widget.destroy()

    # --- LIVE QUEUE ---
    def show_live(self):
        self.clear_main()
        tk.Label(self.main, text="CURRENT LIVE PATIENTS", font=("Arial", 16, "bold"), bg="#1e40af", fg="white", pady=10).pack(fill="x")
        
        # Scrollable Frame
        container = tk.Frame(self.main)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        canvas = tk.Canvas(container, bg="white")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.live_area = tk.Frame(canvas, bg="white")
        
        self.live_area.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.live_area, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        today = datetime.date.today().strftime("%Y-%m-%d")
        db.reference(f"patients/{today}").listen(lambda e: self.root.after(0, self.refresh_live))

    def refresh_live(self):
        for w in self.live_area.winfo_children(): w.destroy()
        today = datetime.date.today().strftime("%Y-%m-%d")
        data = db.reference(f"patients/{today}").get()
        if not data: return

        for dept, patients in data.items():
            if not isinstance(patients, dict): continue
            group = tk.LabelFrame(self.live_area, text=dept.upper(), font=("Arial", 10, "bold"), bg="white", pady=5)
            group.pack(fill="x", pady=5)
            
            for p_id, p in patients.items():
                if isinstance(p, dict):
                    row = tk.Frame(group, bg="white")
                    row.pack(fill="x", padx=10, pady=2)
                    status = "✅" if p.get('checked') else "⏳"
                    # DISPLAY ALL DATA EXCEPT TIMESTAMP
                    info = f"{status} {p.get('token')} | {p.get('name')} ({p.get('age')}Y / {p.get('gender')}) | Dept: {p.get('department', dept)} | Doctor: {p.get('doctor','N/A')}"
                    tk.Label(row, text=info, bg="white", font=("Arial", 10)).pack(side="left")
                    tk.Button(row, text="CHECK", command=lambda d=dept, i=p_id: self.mark_done(d, i)).pack(side="right")

    def mark_done(self, dept, p_id):
        today = datetime.date.today().strftime("%Y-%m-%d")
        db.reference(f"patients/{today}/{dept}/{p_id}").update({"checked": True})
        self.export_to_txt()

    # --- HISTORY TABLE ---
    def show_history(self):
        self.clear_main()
        tk.Label(self.main, text="FULL DATABASE HISTORY", font=("Arial", 16, "bold"), bg="#0f172a", fg="white", pady=10).pack(fill="x")
        
        # Scrollable Treeview
        frame = tk.Frame(self.main)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("Date", "Token", "Name", "Age", "Gender", "Dept", "Doctor", "Status")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.load_history_data()

    def load_history_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        data = db.reference("patients").get()
        if not data: return
        for date, depts in data.items():
            if not isinstance(depts, dict): continue
            for dept, patients in depts.items():
                if not isinstance(patients, dict): continue
                for p_id, p in patients.items():
                    if isinstance(p, dict):
                        stat = "Checked" if p.get('checked') else "Pending"
                        self.tree.insert("", "end", values=(
                            date,
                            p.get('token', 'N/A'),
                            p.get('name', 'N/A'),
                            p.get('age', 'N/A'),
                            p.get('gender', 'N/A'),
                            p.get('department', dept),
                            p.get('doctor','N/A'),
                            stat
                        ))

    # --- TXT EXPORT (WITHOUT TIMESTAMP) ---
    def export_to_txt(self):
        data = db.reference("patients").get()
        if not data: return
        
        try:
            with open("patient_records.txt", "w") as f:
                f.write("RES HELIX - DETAILED PATIENT LOG\n")
                f.write("="*105 + "\n")
                # Table Header
                f.write(f"{'DATE':<12} | {'TOKEN':<12} | {'NAME':<20} | {'AGE':<4} | {'GENDER':<8} | {'DEPT':<15} | {'DOCTOR':<15} | {'STATUS':<10}\n")
                f.write("-"*105 + "\n")
                
                for date, depts in data.items():
                    if not isinstance(depts, dict): continue
                    for dept, patients in depts.items():
                        if not isinstance(patients, dict): continue
                        for p_id, p in patients.items():
                            if isinstance(p, dict):
                                tk_val = p.get('token', 'N/A')
                                nm_val = p.get('name', 'N/A')
                                ag_val = str(p.get('age', 'N/A'))
                                gn_val = p.get('gender', 'N/A')
                                dept_val = p.get('department', dept)
                                doctor_val = p.get('doctor','N/A')
                                st_val = "Checked" if p.get('checked') else "Pending"
                                
                                f.write(f"{date:<12} | {tk_val:<12} | {nm_val:<20} | {ag_val:<4} | {gn_val:<8} | {dept_val:<15} | {doctor_val:<15} | {st_val:<10}\n")
            
            print("Successfully saved detailed records to patient_records.txt")
        except Exception as e:
            print(f"Export Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = HelixAdmin(root)
    root.mainloop()
