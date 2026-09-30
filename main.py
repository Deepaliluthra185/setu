"""
Setu Backend: Multilingual AI Civic Infrastructure Prioritization Platform.
FastAPI Application serving REST endpoints and hosting the control-room frontend.
"""

import os
import json
import io
import csv
from itertools import combinations
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
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


class OptimizeInput(BaseModel):
    budget_cr: float = Field(..., gt=0, example=50.0)


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


@app.post("/complaints/audio")
async def process_audio_complaint(file: UploadFile = File(...)):
    """
    Multimodal grievance intake for vernacular voice notes (.mp3, .wav, .m4a, .ogg).
    Uses Gemini native audio comprehension to transcribe and extract parameters.
    """
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty audio file provided.")

        mime = file.content_type or "audio/mp3"
        nlu_result = nlu.analyze_audio_complaint(contents, mime)

        raw_text = nlu_result.get("transcribed_text", "")
        category = nlu_result.get("category", "General")
        location = nlu_result.get("location", "Unknown")
        urgency = nlu_result.get("urgency", "Normal")
        language_detected = nlu_result.get("language_detected", "Audio")

        complaint_id = db.insert_complaint(
            raw_text=raw_text,
            category=category,
            location=location,
            urgency=urgency,
            language_detected=language_detected
        )

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
            "transcribed_text": raw_text,
            "category": category,
            "location": location,
            "urgency": urgency,
            "language_detected": language_detected,
            "district_matched": district_updated,
            "district_name": district["name"] if district else None,
            "complaints_added": increment_amount
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Failed to process audio complaint: {str(e)}"}
        )


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


def estimate_district_cost_cr(d: Dict[str, Any]) -> float:
    """Estimated capital investment requirement in ₹ Crore based on pop and deficit severity."""
    base = (d["pop"] / 100000.0) * 8.0 * (0.6 + d["infra_gap"])
    return round(max(10.0, min(50.0, base)), 1)


@app.post("/optimize")
async def optimize_budget_allocation(payload: OptimizeInput):
    """
    Automated Capital Allocation Optimizer (0/1 Knapsack Solver).
    Finds the optimal combination of unfunded districts to fund under a given budget (₹ Cr)
    that maximizes national infrastructure coverage gain.
    """
    districts = db.get_all_districts()
    if not districts:
        raise HTTPException(status_code=404, detail="No districts found")

    budget_cr = float(payload.budget_cr)
    scored = scoring.rank_districts(districts)
    unfunded = [d for d in scored if not d["funded"]]

    n = len(districts)
    candidates = []
    for d in unfunded:
        cost = estimate_district_cost_cr(d)
        indiv_gain = round(min(0.35, d["infra_gap"]) / n, 4)
        candidates.append({
            "name": d["name"],
            "category": d["category"],
            "pop": d["pop"],
            "infra_gap": d["infra_gap"],
            "score": d["score"],
            "cost_cr": cost,
            "individual_gain": indiv_gain
        })

    best_combo = []
    best_gain = 0.0
    best_score_sum = 0.0
    best_cost = 0.0

    num_candidates = len(candidates)
    for r in range(1, num_candidates + 1):
        for combo in combinations(candidates, r):
            total_c = sum(c["cost_cr"] for c in combo)
            if total_c <= budget_cr:
                funded_names = set(c["name"].lower() for c in combo)
                curr_covs = [max(0.0, min(1.0, 1.0 - d["infra_gap"])) for d in districts]
                proj_covs = [
                    min(1.0, 1.0 - d["infra_gap"] + 0.35) if (d["funded"] or d["name"].lower() in funded_names)
                    else max(0.0, min(1.0, 1.0 - d["infra_gap"]))
                    for d in districts
                ]
                gain = round((sum(proj_covs) - sum(curr_covs)) / n, 4)
                score_sum = sum(c["score"] for c in combo)

                if (gain > best_gain) or (abs(gain - best_gain) < 1e-5 and score_sum > best_score_sum):
                    best_gain = gain
                    best_score_sum = score_sum
                    best_cost = total_c
                    best_combo = list(combo)

    curr_national = round(sum(max(0.0, min(1.0, 1.0 - d["infra_gap"])) for d in districts) / n, 3)
    proj_national = round(curr_national + best_gain, 3)

    return {
        "budget_cr": budget_cr,
        "allocated_cr": round(best_cost, 1),
        "remaining_cr": round(budget_cr - best_cost, 1),
        "selected_districts": [c["name"] for c in best_combo],
        "selected_count": len(best_combo),
        "current_national_coverage": curr_national,
        "projected_national_coverage": proj_national,
        "gain": round(best_gain, 3),
        "districts_breakdown": [
            {
                "name": c["name"],
                "category": c["category"],
                "cost_cr": c["cost_cr"],
                "priority_score": c["score"],
                "infra_gap_pct": int(round(c["infra_gap"] * 100)),
                "is_recommended": True
            }
            for c in best_combo
        ]
    }


@app.get("/export/csv")
async def export_priorities_csv():
    """
    Exports the complete national infrastructure priority ranking and rationale as a downloadable CSV.
    """
    districts = db.get_all_districts()
    scored = scoring.rank_districts(districts)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "National Rank",
        "District Name",
        "Sector",
        "Priority Score",
        "Total Grievances",
        "Population",
        "Infrastructure Deficit (%)",
        "Estimated Cost (INR Cr)",
        "Funding Status",
        "Equity Factor",
        "Algorithmic Rationale"
    ])

    for idx, d in enumerate(scored, 1):
        cost = estimate_district_cost_cr(d)
        writer.writerow([
            idx,
            d["name"],
            d["category"],
            d["score"],
            d["complaints"],
            d["pop"],
            f"{int(round(d['infra_gap'] * 100))}%",
            f"INR {cost} Cr",
            "Funded (Active)" if d["funded"] else "Unfunded (Candidate)",
            f"{d['equity']}x",
            d["why"]
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="setu_national_priorities.csv"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


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
