import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from agents.ingestion_agent import ingestion_agent
from agents.structuring_agent import structuring_agent
from agents.classification_agent import classification_agent
from agents.risk_agent import risk_agent
from agents.scoring_agent import scoring_agent

class ContractAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Contract Risk Analyzer - Desktop Edition")
        self.root.geometry("1100x700")

        self.current_file = None
        self.clauses_data_map = {}
        self.setup_ui()

    def setup_ui(self):
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        style.configure("Treeview", rowheight=25)

        # === Top Frame: Controls ===
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="Select File", command=self.select_file).pack(side=tk.LEFT, padx=5)
        self.file_label = ttk.Label(top_frame, text="No file selected", font=('Helvetica', 10, 'italic'))
        self.file_label.pack(side=tk.LEFT, padx=5)

        # Separator
        ttk.Separator(top_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=15, fill=tk.Y)

        ttk.Label(top_frame, text="Analyze As:", font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.role_var = tk.StringVar(value="Contractor")
        self.role_dropdown = ttk.Combobox(top_frame, textvariable=self.role_var, state="normal", width=12)
        self.role_dropdown['values'] = ("Contractor", "Client", "Vendor", "Employee", "Freelancer")
        self.role_dropdown.pack(side=tk.LEFT, padx=2)

        ttk.Label(top_frame, text="+ Context:", font=('Helvetica', 10)).pack(side=tk.LEFT, padx=2)
        self.context_var = tk.StringVar(value="")
        self.context_entry = ttk.Entry(top_frame, textvariable=self.context_var, width=20)
        self.context_entry.pack(side=tk.LEFT, padx=2)

        self.analyze_btn = ttk.Button(top_frame, text="Start Analysis", command=self.start_analysis, state=tk.DISABLED)
        self.analyze_btn.pack(side=tk.LEFT, padx=20)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(top_frame, textvariable=self.status_var, foreground="#3b82f6", font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        # === Main Content ===
        main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # --- Left Pane: Stats ---
        left_frame = ttk.Frame(main_frame, width=250, relief=tk.SUNKEN, padding=10)
        main_frame.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Analysis Summary", font=("Helvetica", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))
        self.stats_text = tk.Text(left_frame, wrap=tk.WORD, state=tk.DISABLED, bg=self.root.cget("bg"), bd=0, font=('Helvetica', 11))
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        # --- Right Pane: Master-Detail Split ---
        right_frame = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        main_frame.add(right_frame, weight=4)

        # 1) Top: Table (Master)
        table_frame = ttk.Frame(right_frame)
        right_frame.add(table_frame, weight=2)

        columns = ("ID", "Category", "Risk")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
            w = 80 if col == "ID" else 150 if col == "Risk" else 200
            self.tree.column(col, width=w, anchor=tk.W)

        # Scrollbar for Table
        table_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=table_scroll.set)
        table_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 2) Bottom: Details (Detail)
        detail_frame = ttk.Frame(right_frame, padding=10, relief=tk.SUNKEN)
        right_frame.add(detail_frame, weight=1)

        ttk.Label(detail_frame, text="Clause Details", font=("Helvetica", 14, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.detail_text = tk.Text(detail_frame, wrap=tk.WORD, state=tk.DISABLED, bg=self.root.cget("bg"), bd=0, font=('Helvetica', 11))
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        
        # Tags for styling
        self.tree.tag_configure("High", background="#fee2e2")    # Light red
        self.tree.tag_configure("Medium", background="#fef3c7")  # Light amber
        self.tree.tag_configure("Low", background="#d1fae5")     # Light green

    def select_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("PDF Files", "*.pdf"), ("Word Docs", "*.docx"), ("Images", "*.png;*.jpg"), ("All Files", "*.*")]
        )
        if filepath:
            self.current_file = filepath
            self.file_label.config(text=os.path.basename(filepath))
            self.analyze_btn.config(state=tk.NORMAL)

    def start_analysis(self):
        if not self.current_file:
            return

        self.analyze_btn.config(state=tk.DISABLED)
        self.update_status("Analyzing... (This may take several minutes if using full LLM mode)")
        
        # Clear previous data
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.config(state=tk.DISABLED)

        # Run pipeline in a separate thread so the GUI doesn't freeze
        threading.Thread(target=self.run_pipeline, daemon=True).start()

    def run_pipeline(self):
        try:
            base_role = self.role_var.get().strip() or "Contractor"
            extra_context = self.context_var.get().strip()
            
            if extra_context:
                role = f"{base_role} ({extra_context})"
            else:
                role = base_role
            
            # Step 1
            self.update_status(f"[1/5] Ingesting {os.path.basename(self.current_file)}...")
            ingested = ingestion_agent(self.current_file)
            if ingested["status"] != "success":
                raise Exception(ingested.get("error", "Ingestion failed"))
            raw_text = ingested["raw_text"]

            # Step 2
            self.update_status("[2/5] Structuring document tree...")
            structured = structuring_agent(raw_text)

            # Step 3
            self.update_status("[3/5] Classifying clauses using AI (Takes time!)...")
            classified = classification_agent(structured)

            # Step 4
            self.update_status(f"[4/5] Performing Risk Analysis for '{role}' (Takes time!)...")
            risk_result = risk_agent(classified, user_role=role)

            # Step 5
            self.update_status("[5/5] Calculating Overall Contract Score...")
            score_result = scoring_agent(risk_result.get("clauses", []))

            self.root.after(0, self.display_results, risk_result, score_result)

        except Exception as e:
            self.root.after(0, self.display_error, str(e))

    def update_status(self, msg):
        self.root.after(0, self.status_var.set, msg)

    def display_results(self, data, score_data):
        self.update_status("✅ Analysis Complete.")
        self.analyze_btn.config(state=tk.NORMAL)

        # Build stats
        clauses = data.get("clauses", [])
        total_clauses = len(clauses)
        
        overall_score = score_data.get("overall_score", 0.0)
        risk_counts = score_data.get("summary", {"high": 0, "medium": 0, "low": 0})
        cat_counts = {}
        for c in clauses:
            t = c.get("type", "Other")
            cat_counts[t] = cat_counts.get(t, 0) + 1

        # Use stars/emojis based on score (Lower risk = better)
        if overall_score > 66:
            score_eval = "HIGH RISK 🚨"
        elif overall_score > 33:
            score_eval = "MODERATE RISK ⚠️"
        else:
            score_eval = "LOW RISK ✅"

        stats_lines = [
            f"🎯 OVERALL SCORE",
            f"{overall_score}/100 ({score_eval})",
            f"\n📊 SUMMARY",
            f"Total Clauses: {total_clauses}",
            f"\n🔥 RISK BREAKDOWN",
            f"High Risk:   {risk_counts.get('high', 0)}",
            f"Medium Risk: {risk_counts.get('medium', 0)}",
            f"Low Risk:    {risk_counts.get('low', 0)}",
            f"\n📑 CATEGORIES"
        ]
        for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
            stats_lines.append(f"{cat}: {count}")

        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.insert(tk.END, "\n".join(stats_lines))
        self.stats_text.config(state=tk.DISABLED)

        # Populate tree and map
        self.clauses_data_map.clear()
        for i, c in enumerate(clauses):
            c_id = c.get("id", str(i))
            c_type = c.get("type", "Other")
            c_risk = c.get("risk", "Low")
            
            self.clauses_data_map[str(c_id)] = c
            self.tree.insert("", tk.END, values=(c_id, c_type, c_risk), tags=(c_risk,))

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item_data = self.tree.item(selected_items[0])
        c_id = str(item_data['values'][0])
        c = self.clauses_data_map.get(c_id)
        
        if c:
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete(1.0, tk.END)
            
            c_type = c.get("type", "Other")
            c_risk = c.get("risk", "Low")
            c_reason = c.get("reason", "No reason provided.")
            c_text = c.get("text", "")
            
            content = f"ID: {c_id}  |  Category: {c_type}  |  Risk Level: {c_risk}\n"
            content += f"{'-'*60}\n"
            content += f"RISK EXPLANATION:\n{c_reason}\n\n"
            content += f"{'-'*60}\n"
            content += f"FULL CLAUSE TEXT:\n{c_text}"
            
            self.detail_text.insert(tk.END, content)
            self.detail_text.config(state=tk.DISABLED)

    def display_error(self, err_msg):
        self.update_status("❌ Analysis failed.")
        self.analyze_btn.config(state=tk.NORMAL)
        messagebox.showerror("Error", err_msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = ContractAnalyzerGUI(root)
    root.mainloop()
