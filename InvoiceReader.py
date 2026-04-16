import os
import json
from datetime import datetime, timedelta
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
dayspan = 0
json_file_path = "invoice_data.json"
config_file_path = "folder_config.json"

existing_invoice_numbers: set = set()


# ---------------------------------------------------------------------------
# PDF Extraction
# ---------------------------------------------------------------------------

def _extract(pattern: str, text: str, flags=re.DOTALL) -> Optional[str]:
    """Return first capture group of pattern match, or None."""
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def extract_service_lines(full_text: str) -> List[Dict]:
    """
    Split the full invoice text on each 'Claim number' header and parse
    one service-line dict per block.
    """
    service_lines = []

    # Each repeating block starts with 'Claim number'
    blocks = re.split(r'(?=Claim number)', full_text)

    for block in blocks:
        # Skip blocks that don't contain a service date (e.g. header fragments)
        if "Service date" not in block:
            continue

        service_date = _extract(r'Service date\s+(\d{2}/\d{2}/\d{4})', block)
        service_code = _extract(r'Service code\s+(\w+)', block)
        amount_str   = _extract(r'Amount\s+\$([\d,]+\.\d{2})', block)

        # Duration is stored as "H : MM" — normalise to "H:MM"
        dur_match = re.search(r'\(HH:MM\)\s+(\d+)\s*:\s*(\d+)', block)
        if dur_match:
            duration = f"{dur_match.group(1)}:{dur_match.group(2).zfill(2)}"
        else:
            duration = None

        if service_date and amount_str:
            service_lines.append({
                "service_date": service_date,
                "service_code": service_code,
                "duration_hhmm": duration,
                "amount": float(amount_str.replace(",", ""))
            })

    return service_lines


def extract_invoice_data(file_path: str) -> dict:
    """
    Open a PDF and return a structured invoice dict containing top-level
    invoice/client fields plus a list of individual service lines.
    """
    doc = fitz.open(file_path)
    full_text = "".join(page.get_text() for page in doc)

    # --- Invoice-level fields ---
    invoice_number = _extract(r'Invoice number[:\s]+([\w\d]+)', full_text)
    client_name    = _extract(r'Client\s+([A-Za-z ]+?)\s+DOB', full_text)
    claim_number   = _extract(r'Claim number\s+([\w\d]+)', full_text)
    dob            = _extract(r'DOB\s+(\d{2}/\d{2}/\d{4})', full_text)
    provider_id    = _extract(r'Provider ID\s+([\w\d]+)', full_text)
    date_issued    = _extract(r'Date issued to ACC\s+(\d{2}/\d{2}/\d{4})', full_text)
    total_str      = _extract(r'Total invoiced.*?\$([\d,]+\.\d{2})', full_text)

    total_invoiced = float(total_str.replace(",", "")) if total_str else 0.0

    # --- Per-line service data ---
    service_lines = extract_service_lines(full_text)

    return {
        "invoice_number": invoice_number,
        "file_name":      os.path.basename(file_path),
        "date_issued":    date_issued,
        "modified_date":  datetime.fromtimestamp(
                              os.path.getmtime(file_path)
                          ).strftime("%Y-%m-%d %H:%M:%S"),
        "client_name":    client_name,
        "claim_number":   claim_number,
        "dob":            dob,
        "provider_id":    provider_id,
        "total_invoiced": total_invoiced,
        "service_lines":  service_lines,
    }


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def get_recent_pdfs(folder_path: str, days: int = dayspan) -> List[str]:
    """Return PDF files whose name contains 'Invoice Submission', modified
    within the last *days* days.  days=0 returns all matching files."""
    cutoff = datetime.min if days == 0 else datetime.now() - timedelta(days=days)

    recent_files = []
    for file in os.listdir(folder_path):
        if "Invoice Submission" not in file:
            continue
        file_path = os.path.join(folder_path, file)
        if not (file.lower().endswith(".pdf") and os.path.isfile(file_path)):
            continue

        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        if days == 0 or mod_time.date() > cutoff.date():
            recent_files.append(file_path)
        elif mod_time.date() == cutoff.date() and mod_time > cutoff:
            recent_files.append(file_path)

    recent_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return recent_files


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------

def load_existing_invoice_numbers() -> None:
    """Populate the global set with invoice numbers already in the JSON store."""
    global existing_invoice_numbers
    try:
        if os.path.exists(json_file_path):
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing_invoice_numbers = {
                inv["invoice_number"]
                for inv in data.get("invoices", [])
                if inv.get("invoice_number")
            }
        else:
            existing_invoice_numbers = set()
    except Exception as e:
        print(f"Error loading invoice numbers: {e}")
        existing_invoice_numbers = set()


def save_to_json(new_invoices: List[Dict]) -> None:
    """
    Append *new_invoices* to the JSON store and refresh the metadata block.

    File structure:
    {
        "metadata": { "total_invoices": N, "total_amount": X, "last_updated": "..." },
        "invoices": [ { ...invoice... }, ... ]
    }
    """
    try:
        if os.path.exists(json_file_path):
            with open(json_file_path, "r", encoding="utf-8") as f:
                store = json.load(f)
        else:
            store = {"invoices": []}

        store["invoices"].extend(new_invoices)

        store["metadata"] = {
            "total_invoices": len(store["invoices"]),
            "total_amount":   round(
                sum(inv.get("total_invoiced", 0) for inv in store["invoices"]), 2
            ),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"Error saving to JSON: {e}")


# ---------------------------------------------------------------------------
# Folder config persistence
# ---------------------------------------------------------------------------

def load_folder_config() -> str:
    default = ""
    try:
        if os.path.exists(config_file_path):
            with open(config_file_path, "r", encoding="utf-8") as f:
                return json.load(f).get("last_folder", default)
    except Exception as e:
        print(f"Error loading folder config: {e}")
    return default


def save_folder_config(folder_path: str) -> None:
    try:
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump({"last_folder": folder_path}, f, indent=2)
    except Exception as e:
        print(f"Error saving folder config: {e}")


# ---------------------------------------------------------------------------
# Processing pipeline
# ---------------------------------------------------------------------------

def process_invoices(folder_path: str, dayspan_value: int,
                     output_text: tk.Text) -> None:
    """Scan folder, extract invoices, deduplicate, save, and report totals."""

    income_sum = 0.0

    def log(msg: str) -> None:
        output_text.insert(tk.END, msg + "\n")
        output_text.see(tk.END)
        output_text.update()

    try:
        log(f"Scanning {folder_path} for recent invoices...")
        load_existing_invoice_numbers()

        pdf_files = get_recent_pdfs(folder_path, dayspan_value)
        if not pdf_files:
            log("No matching PDF files found.")
            return

        results: List[Dict] = []
        skipped_count = 0

        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                log(f"Processing {i}/{len(pdf_files)}: {os.path.basename(pdf_file)}")
                invoice_data = extract_invoice_data(pdf_file)

                inv_no = invoice_data["invoice_number"]
                if inv_no and inv_no in existing_invoice_numbers:
                    log(f"  Skipping duplicate invoice: {inv_no}")
                    skipped_count += 1
                    continue

                line_count = len(invoice_data["service_lines"])
                log(f"  → {line_count} service line(s), total: "
                    f"${invoice_data['total_invoiced']:.2f}")

                results.append(invoice_data)
                income_sum += invoice_data["total_invoiced"]
                if inv_no:
                    existing_invoice_numbers.add(inv_no)

            except Exception as e:
                log(f"  Error processing {os.path.basename(pdf_file)}: {e}")

        # Persist
        if results:
            save_to_json(results)
            log(f"\nSaved {len(results)} new invoice(s) to {json_file_path}. "
                f"Skipped {skipped_count} duplicate(s).")
        else:
            log(f"\nNo new invoices found. Skipped {skipped_count} duplicate(s).")

        # Summary stats
        if dayspan_value > 0:
            weekspan = round(dayspan_value / 7, 2)
            avg = round(income_sum / 2 / weekspan, 2) if weekspan else 0
            log(f"Total: ${income_sum:.2f}  |  Span: {weekspan} weeks  |  "
                f"Avg: ${avg:.2f}/week")
        else:
            log(f"Total: ${income_sum:.2f}  (all files)")

        log("\n" + "=" * 50)

    except Exception as e:
        log(f"Fatal error during processing: {e}")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

def create_main_window() -> tk.Tk:
    root = tk.Tk()
    root.title("Invoice Processor")
    root.geometry("600x500")
    root.resizable(True, True)
    root.eval("tk::PlaceWindow . center")

    dayspan_var   = tk.IntVar(value=dayspan)
    folder_var    = tk.StringVar(value=load_folder_config())

    def browse_folder() -> None:
        selected = filedialog.askdirectory(
            title="Select Invoice Folder",
            initialdir=folder_var.get()
        )
        if selected:
            folder_var.set(selected)
            save_folder_config(selected)

    def on_process() -> None:
        if not os.path.exists(folder_var.get()):
            messagebox.showerror("Error", "Selected folder does not exist!")
            return
        output_text.delete(1.0, tk.END)
        process_btn.config(state="disabled")
        root.after(100, lambda: [
            process_invoices(folder_var.get(), dayspan_var.get(), output_text),
            process_btn.config(state="normal"),
        ])

    # ---- Layout ----
    main = ttk.Frame(root, padding="10")
    main.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    main.columnconfigure(1, weight=1)
    main.rowconfigure(4, weight=1)

    ttk.Label(main, text="Invoice Processor", font=("Arial", 16, "bold")).grid(
        row=0, column=0, columnspan=3, pady=(0, 20))

    # Folder row
    ttk.Label(main, text="Folder:").grid(row=1, column=0, sticky="w", pady=(0, 10))
    ttk.Entry(main, textvariable=folder_var, width=50).grid(
        row=1, column=1, sticky="ew", pady=(0, 10), padx=(5, 5))
    ttk.Button(main, text="Browse", command=browse_folder).grid(
        row=1, column=2, pady=(0, 10))

    # Day span row
    ttk.Label(main, text="Day span (0 for all):").grid(
        row=2, column=0, sticky="w", pady=(0, 10))
    ttk.Entry(main, textvariable=dayspan_var, width=10).grid(
        row=2, column=1, sticky="w", pady=(0, 10), padx=(5, 0))

    # Info + process button
    ttk.Label(main, text="0 = all files  |  N = files modified within last N days",
              font=("Arial", 9), foreground="gray").grid(
        row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))
    process_btn = ttk.Button(main, text="Process Invoices", command=on_process)
    process_btn.grid(row=3, column=2, pady=(0, 10))

    # Output area
    out_frame = ttk.LabelFrame(main, text="Processing Output", padding="5")
    out_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
    out_frame.columnconfigure(0, weight=1)
    out_frame.rowconfigure(0, weight=1)

    output_text = tk.Text(out_frame, height=15, wrap=tk.WORD)
    scrollbar   = ttk.Scrollbar(out_frame, orient=tk.VERTICAL,
                                command=output_text.yview)
    output_text.configure(yscrollcommand=scrollbar.set)
    output_text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    return root


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = create_main_window()
    root.mainloop()