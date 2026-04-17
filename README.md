# 🧾 Invoice Processor (Healthcare Workflow Automation)

A Python-based desktop tool that automatically extracts, processes, and aggregates invoice data from PDF files — designed for real-world clinical workflows.

This project was built to reduce manual administrative workload in healthcare settings, particularly for ACC (Accident Compensation Corporation) invoice processing in New Zealand.

---

## 🚀 Key Features

* 📄 **Automatic PDF Parsing**

  * Extracts structured invoice data from semi-structured PDF documents
  * Supports multiple service lines per invoice

* 🧠 **Workflow-Aware Processing**

  * Filters relevant files based on naming conventions (e.g. *Invoice Submission*)
  * Processes only recent files (configurable day span)

* 🔁 **Duplicate Detection**

  * Prevents re-processing of previously recorded invoices

* 💾 **Persistent Storage**

  * Stores all processed data in a structured JSON database
  * Automatically maintains metadata:

    * Total invoices
    * Total revenue
    * Last updated timestamp

* 🖥️ **Simple GUI Interface**

  * Built with Tkinter for easy use by non-technical clinic staff

---

## 🧩 Example Output Structure

```json
{
  "metadata": {
    "total_invoices": 25,
    "total_amount": 12450.00,
    "last_updated": "2026-04-10 14:32:00"
  },
  "invoices": [
    {
      "invoice_number": "ABC12345",
      "client_name": "John Doe",
      "total_invoiced": 120.00,
      "service_lines": [
        {
          "service_date": "01/04/2026",
          "service_code": "ACU001",
          "duration_hhmm": "1:00",
          "amount": 120.00
        }
      ]
    }
  ]
}
```

---

## 🛠️ Tech Stack

* Python 3.9+
* PyMuPDF (`fitz`) — PDF text extraction
* Tkinter — GUI interface
* Regex — structured data parsing
* JSON — lightweight data persistence

---

## 📦 Installation

```bash
git clone https://github.com/ethan-nz/InvoiceReader/InvoiceReader.py
cd InvoiceReader

pip install -r requirements.txt
```

If `requirements.txt` is not available:

```bash
pip install pymupdf
```

---

## ▶️ Usage

Run the application:

```bash
python InvoiceReader.py
```

Steps:

1. Select the folder containing invoice PDFs
2. Set day span:

   * `0` = process all files
   * `N` = process files modified in last N days
3. Click **Process Invoices**

---

## 💡 Real-World Use Case

This tool was developed in a clinical environment where:

* Staff manually read PDF invoices
* Re-entered data into systems
* Tracked totals manually

The tool reduces:

* Manual data entry time
* Human error
* Duplicate processing

---

## ⚠️ Limitations

* Parsing relies on consistent PDF structure
* Regex patterns may need adjustment for different invoice formats
* Currently GUI-only (no CLI support yet)

---

## 🔮 Future Improvements

* CLI mode for automation pipelines
* Configurable parsing rules (JSON/YAML-based)
* Integration with clinic management systems
* Local-first AI agent for adaptive document parsing
* Export to CSV / database (SQLite/PostgreSQL)

---

## 🎯 Project Context

This project is part of a broader initiative:

> **Healthcare Workflow Automation & System Integration**

Focused on:

* Reducing administrative burden in clinics
* Bridging disconnected healthcare systems
* Enabling automation without requiring full system migration

---

## 👤 Author

Ethan
Healthcare Workflow Automation Engineer (transitioning)
13+ years clinical experience + Python-based automation
