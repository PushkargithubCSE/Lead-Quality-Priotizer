# Lead Quality Scorer & Prioritizer - Full Prototype

This document describes the full folder structure, files, and instructions to run the **Lead Quality Scorer & Prioritizer** with **UI + backend + scoring logic**.

---

## 📂 Folder Structure

```
leadgen_prototype/
├── backend/
│   ├── lead_quality_prioritizer.py   # Python scoring & prioritization logic
│   ├── fastapi_lead_backend.py       # FastAPI backend to expose API endpoints
│   └── requirements.txt              # Python dependencies
│
├── frontend/
│   ├── LeadDashboard.jsx             # React frontend component
│   ├── package.json                  # React project dependencies
│   ├── public/                        # Standard React public folder
│   └── src/                           # Standard React src folder
│
├── sample_data/
│   └── leads_input.csv               # Example CSV for testing
│
└── README.md                         # This file
```

---

## 🛠️ Backend Setup

1. Navigate to the backend folder:

```bash
cd backend
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:

```bash
python fastapi_lead_backend.py
```

The backend will run at: `http://localhost:8000`.

**Endpoints:**

* `POST /score` → accepts CSV file, returns scored leads as JSON.

---

## 🖥️ Frontend Setup

1. Navigate to the frontend folder:

```bash
cd frontend
```

2. Install Node.js dependencies:

```bash
npm install
```

3. Start the React app:

```bash
npm start
```

The UI will open in the browser at `http://localhost:3000`.

**Features:**

* Upload CSV leads
* View scored leads in table
* Filter by minimum score
* Download prioritized leads CSV
* Color-coded score visualization

**Note:** The frontend calls the backend API at `http://localhost:8000/score`.

---



## ✅ How It Works

1. User uploads CSV via the **React UI**.
2. Frontend sends the file to **FastAPI backend**.
3. Backend calls **lead_quality_prioritizer.py** scoring logic.
4. Backend returns scored leads JSON.
5. Frontend displays table with score, status, and color coding.
6. Users can filter and download **prioritized leads** CSV.

---

## ⚡ Optional Enhancements

* Add **tooltip** or modal to show score breakdown per lead.
* Integrate enrichment APIs like **Clearbit or Hunter**.
* Add **pagination** for large CSVs.
* Use **fuzzy deduplication** for messy data.

---

🧠 Lead Quality Scorer & Prioritizer

A lightweight Python tool that scores, deduplicates, and prioritizes scraped B2B leads to help marketing and sales teams spend enrichment credits more efficiently.

🚀 Overview

This project was built as a 5-hour MVP challenge for a SaaSquatch Leads–style lead generation platform.
It focuses on improving lead quality and credit efficiency by automatically finding which scraped leads are worth enriching first.

Instead of enriching every lead, the tool scores each lead from 0–100 using explainable rules and then selects the best ones within your credit budget.

🎯 Key Features

🧩 Lead Scoring — Rates leads (0–100) based on completeness, seniority, email validity, domain match, and company strength.

🔍 Deduplication — Automatically removes duplicates using email or name+domain.

🎯 Prioritization — Chooses top-scoring leads to enrich within your available credits.

⚙️ CSV → CSV Workflow — Simple command-line interface; no complex setup.

🧠 Explainable Output — Each lead includes a JSON breakdown of score components.

🌐 Optional MX Check — Validates if an email domain actually exists (requires dnspython).

🛠️ Installation
git clone https://github.com/yourusername/lead-quality-prioritizer.git
cd lead-quality-prioritizer
pip install -r requirements.txt  # optional if you use MX check or tldextract


(Optional libraries: dnspython, tldextract)

💻 Usage
python lead_quality_prioritizer.py \
  --input leads_input.csv \
  --scored scored.csv \
  --priority prioritized.csv \
  --credits 10


Optional flags:

--mx-check → run MX record validation (slower, requires internet).

--no-dedupe → skip deduplication.

--cost-per-enrich → set credit cost per lead (default 1).

Example:

python lead_quality_prioritizer.py --input leads.csv --scored out.csv --priority top.csv --credits 50

📊 Example Output
name	email	job_title	score	score_breakdown
Alice Smith	alice@acme.com
	VP Sales	92	{"completeness":1.0,"seniority":0.9,"email_validity":1.0,"domain_match":1.0}
Bob Jones	bob@gmail.com
	Developer	35	{"completeness":0.6,"seniority":0.3,"email_validity":0.3}
🧩 How It Works

Each lead is scored on:

Completeness → email, phone, LinkedIn, company info

Seniority → job title keywords (e.g., CEO, VP, Director)

Email Validity → syntax check + personal domain penalty

Domain Match → checks if email matches company domain

Company Signal → non-personal domain or estimated revenue

The weighted total gives a 0–100 lead quality score.
