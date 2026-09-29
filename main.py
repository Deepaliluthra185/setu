"""
Setu Backend: Multilingual AI Civic Infrastructure Prioritization Platform.
FastAPI Application serving REST endpoints and hosting the control-room frontend.
"""

import os
import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import db
import scoring
import nlu

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
CPGRAMS_FILE = DATA_DIR / "cpgrams.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and seed synthetic districts
    db.init_db()
    yield


app = FastAPI(
    title="Setu - Multilingual AI Civic Infrastructure Engine",
    description="Transforms citizen development grievances into explainable, prioritized national infrastructure recommendations.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local testing flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Schemas
class ComplaintInput(BaseModel):
    text: str = Field(..., example="Paani nahi aa raha Rampur mein 4 din se, tanker turant bhejo khatra hai")


class SimulateInput(BaseModel):
    funded: List[str] = Field(..., example=["Rampur", "Devnagar"])


# Endpoints
@app.post("/complaints")
async def process_complaint(payload: ComplaintInput):
    """
    Ingests citizen complaint, executes two-layer multilingual NLU,
    logs record into SQLite, and increments district complaint counter (+3 if urgent, +1 otherwise).
    """
    raw_text = payload.text or ""
    nlu_result = nlu.analyze_complaint(raw_text)

    category = nlu_result["category"]
    location = nlu_result["location"]
    urgency = nlu_result["urgency"]
    language_detected = nlu_result["language_detected"]

    # Log complaint in DB
    complaint_id = db.insert_complaint(
        raw_text=raw_text,
        category=category,
        location=location,
        urgency=urgency,
        language_detected=language_detected
    )

    # Check if location maps to a known district
    district = db.get_district(location) if location != "Unknown" else None
    increment_amount = 0
    district_updated = False

    if district:
        increment_amount = 3 if urgency == "Urgent" else 1
        db.increment_district_complaints(district["name"], increment_amount)
        district_updated = True

    return {
        "status": "success",
        "complaint_id": complaint_id,
        "category": category,
        "location": location,
        "urgency": urgency,
        "language_detected": language_detected,
        "district_matched": district_updated,
        "district_name": district["name"] if district else None,
        "complaints_added": increment_amount
    }


@app.get("/districts")
async def list_districts():
    """Returns all districts with current data from database."""
    districts = db.get_all_districts()
    return districts


@app.get("/ranking")
async def get_district_ranking():
    """
    Returns districts scored by the explainable scoring engine,
    sorted by score descending with human-readable 'why' rationale.
    """
    districts = db.get_all_districts()
    ranked = scoring.rank_districts(districts)
    return ranked


@app.post("/simulate")
async def simulate_infrastructure_funding(payload: SimulateInput):
    """
    What-if simulator:
    Calculates current vs projected national coverage index based on proposed funded districts.
    Projected coverage for funded districts: min(1 - infra_gap + 0.35, 1.0).
    """
    districts = db.get_all_districts()
    if not districts:
        raise HTTPException(status_code=404, detail="No districts found")

    funded_set = set(name.strip().lower() for name in payload.funded)

    district_projections = []
    current_coverages = []
    projected_coverages = []

    for d in districts:
        infra_gap = d["infra_gap"]
        curr_cov = max(0.0, min(1.0, 1.0 - infra_gap))
        
        is_selected = d["name"].lower() in funded_set
        if is_selected:
            proj_cov = min(1.0, 1.0 - infra_gap + 0.35)
        else:
            proj_cov = curr_cov

        current_coverages.append(curr_cov)
        projected_coverages.append(proj_cov)

        district_projections.append({
            "name": d["name"],
            "category": d["category"],
            "infra_gap": infra_gap,
            "was_funded_previously": d["funded"],
            "selected_in_simulation": is_selected,
            "current_coverage": round(curr_cov, 3),
            "projected_coverage": round(proj_cov, 3),
            "coverage_gain": round(proj_cov - curr_cov, 3)
        })

    nat_curr = round(sum(current_coverages) / len(current_coverages), 3)
    nat_proj = round(sum(projected_coverages) / len(projected_coverages), 3)
    delta = round(nat_proj - nat_curr, 3)

    return {
        "current_national_coverage": nat_curr,
        "projected_national_coverage": nat_proj,
        "gain": delta,
        "total_districts": len(districts),
        "funded_count": len(funded_set),
        "district_projections": district_projections
    }


@app.get("/impact")
async def get_impact_trajectory():
    """
    For funded districts, returns a simulated 6-month complaint decline
    modeling post-commissioning resolution (15% monthly decay rate).
    Clearly labeled as simulated.
    """
    districts = db.get_all_districts()
    funded_districts = [d for d in districts if d["funded"]]

    if not funded_districts:
        return {
            "is_simulated": True,
            "decay_rate": "15% monthly decay",
            "message": "No districts currently marked as funded in the database.",
            "funded_districts": []
        }

    results = []
    for d in funded_districts:
        c0 = d["complaints"]
        trajectory = []
        for m in range(7):
            val = max(0, int(round(c0 * (0.85 ** m))))
            trajectory.append({
                "month": m,
                "label": f"M{m}",
                "complaints": val
            })
        
        m6_val = trajectory[-1]["complaints"]
        drop_pct = round(((c0 - m6_val) / max(c0, 1)) * 100, 1)

        results.append({
            "name": d["name"],
            "category": d["category"],
            "initial_complaints": c0,
            "projected_m6_complaints": m6_val,
            "overall_drop_percentage": drop_pct,
            "trajectory": trajectory
        })

    return {
        "is_simulated": True,
        "decay_model": "15% monthly decay following project commissioning",
        "description": "Synthetic 6-month post-funding resolution model for infrastructure impact tracking.",
        "funded_districts": results
    }


@app.get("/trends")
async def get_cpgrams_trends():
    """
    Returns authentic CPGRAMS trend data (Jan-Jun 2026) and state category distributions.
    """
    if not CPGRAMS_FILE.exists():
        raise HTTPException(status_code=404, detail="CPGRAMS dataset file missing")
    
    with open(CPGRAMS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# Serve Frontend
@app.get("/")
async def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse(
            status_code=200,
            content={"message": "Setu API is running. Frontend index.html will be served here."}
        )
    return FileResponse(index_file)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
