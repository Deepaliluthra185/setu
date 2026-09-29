# Setu (सेतु) - Multilingual AI Civic Infrastructure Platform

> **From Fragmented Grievances to Prioritized Capital Investments.**  
> Setu transforms citizen development grievances across fragmented portals and regional vernaculars into explainable, prioritized national infrastructure recommendations.

---

## 🏛️ Overview

Public complaints often arrive across fragmented portals, in Romanized regional dialects (Hinglish, Punjabi, etc.), disconnected from ground infrastructure deficit indices. Setu bridges the gap by fusing natural language demand with demographic density, baseline infrastructure deficit indices, and capital coverage metrics.

### Key Pillars
1. **Multilingual NLU & Multimodal Audio Intake**: Two-layer classifier (Fast offline keyword engine + Google Gemini 2.5 Flash hybrid classification) supporting text and audio file uploads (`.mp3`, `.wav`, `.m4a`) in English, Romanized Hindi, Punjabi, and code-switched vernacular.
2. **Explainable Priority Algorithm**: Dynamic scoring balancing demand intensity, baseline infrastructure deficit index, and small-district equity boosts.
3. **Interactive Control Room**: SVG Spatial Demand Hotspot map, live District Inspector, and top action ranking.
4. **Capital Budget Optimizer**: Automated 0/1 Knapsack solver finding mathematically optimal district combinations under arbitrary budget limits (₹ Cr).
5. **Authentic CPGRAMS Baseline**: Grounded with DARPG monthly grievance data and state-level category distributions.
6. **What-If Capital Allocation Simulator**: Interactive policy simulator projecting national infrastructure coverage gains.
7. **Post-Funding Resolution Trajectories**: 6-month post-commissioning decay models for tracking long-term outcomes.
8. **One-Click Dossier Export**: Instant CSV download and print-ready executive briefing summaries for policymakers.
9. **BRICS Shared Model Simulation**: Illustrative privacy-preserving federated learning across partner nations.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Microsoft Edge or Chromium (for Playwright E2E tests)

### 2. Installation
```bash
git clone https://github.com/Deepaliluthra185/setu.git
cd setu

# Install Python dependencies
pip install -r requirements.txt

# (Optional) Install Playwright browser dependencies for E2E tests
playwright install
```

### 3. Environment Configuration
Copy the example environment file and add your Gemini API key (optional, offline fallback is enabled by default):
```bash
cp .env.example .env
```
In `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Running the Platform
Start the FastAPI server:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
Open your browser at:
- **Control Room Dashboard**: [http://localhost:8000](http://localhost:8000)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Automated Testing

### Backend Unit & Integration Tests
Runs 12 diverse test cases across languages, edge cases, what-if simulations, and CPGRAMS verification:
```bash
python test_backend.py
```

### Frontend Playwright E2E Tests
Runs automated browser testing across the entire dashboard and captures a full-page verification screenshot:
```bash
python test_frontend_e2e.py
```

---

## 📂 Project Architecture

```
setu/
├── data/
│   ├── cpgrams.json           # Authentic DARPG grievance baseline data
│   └── districts.csv          # District demographic & baseline deficit benchmark
├── frontend/
│   └── index.html             # Glassmorphic, responsive control room dashboard
├── .env.example               # Template environment file
├── .gitignore                 # Protected secrets and build cache
├── db.py                      # SQLite persistence and schema initialization
├── main.py                    # FastAPI application, routing, and static file hosting
├── nlu.py                     # Hybrid NLU engine (Google GenAI + Offline Keyword Rules)
├── requirements.txt           # Python package dependencies
├── scoring.py                 # Algorithmic priority score calculations
├── test_backend.py            # API endpoint test suite
└── test_frontend_e2e.py       # Playwright browser end-to-end test suite
```

---

## 🛡️ Governance & Human-in-the-Loop

Setu generates explainable recommendations for policymakers. It does not automatically allocate statutory capital; all proposals undergo administrative and legislative scrutiny.
