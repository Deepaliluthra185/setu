"""
Automated validation script for Setu Backend API.
Tests all endpoints including 12 diverse sample complaints and edge cases.
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("=== TESTING SETU BACKEND ===")
    
    # 1. Test GET /districts
    res = requests.get(f"{BASE_URL}/districts")
    assert res.status_code == 200, f"GET /districts failed: {res.text}"
    districts = res.json()
    print(f"[OK] GET /districts returned {len(districts)} districts")
    assert len(districts) == 9

    # 2. Test GET /ranking
    res = requests.get(f"{BASE_URL}/ranking")
    assert res.status_code == 200, f"GET /ranking failed: {res.text}"
    ranked = res.json()
    print(f"[OK] GET /ranking returned {len(ranked)} ranked districts. Top district: {ranked[0]['name']} (Score: {ranked[0]['score']})")
    assert "why" in ranked[0]
    assert "demand" in ranked[0]

    # 3. Test 12 sample complaints across English, Hindi romanized, Punjabi, Mixed, Empty, Unknown location
    samples = [
        ("Water pipeline broken near primary school in Rampur, needs repair", "Rampur", "Water", "Normal", "English"),
        ("Devnagar mein bijli ka taar gir gaya hai turant aao bohot bada khatra hai", "Devnagar", "Power", "Urgent", "Hindi (Romanized)"),
        ("Kotwali me naali ka kachra safai nahi hua hai badbu aa rahi hai", "Kotwali", "Sanitation", "Normal", "Hindi (Romanized)"),
        ("Severe bridge collapse hazard on main road in Bharatpur, immediate help needed!", "Bharatpur", "Roads", "Urgent", "English"),
        ("Sundargram health clinic me doctor nahi hai dawai bhi khatam urgent attention please", "Sundargram", "Health", "Urgent", "Mixed"),
        ("Pind vich paani di samasya bohot zyada hai Chandanpur ch tanker bhejo", "Chandanpur", "Water", "Normal", "Punjabi"),
        ("", "Unknown", "General", "Normal", "English"),
        ("   ", "Unknown", "General", "Normal", "English"),
        ("Sadak par bohot khadde hain accident ho rahe hain", "Unknown", "Roads", "Normal", "Hindi (Romanized)"),
        ("Nirmalpur main high voltage transformer blast khatra urgent", "Nirmalpur", "Power", "Urgent", "Hindi (Romanized)"),
        ("Vasant Vihar street drain overflowing with dirty water and waste", "Vasant Vihar", "Sanitation", "Normal", "English"),
        ("Anantpur hospital needs more beds and medical staff", "Anantpur", "Health", "Normal", "English")
    ]

    print("\n--- Testing POST /complaints with 12 diverse sample cases ---")
    for idx, (text, exp_loc, exp_cat, exp_urg, exp_lang) in enumerate(samples, 1):
        res = requests.post(f"{BASE_URL}/complaints", json={"text": text})
        assert res.status_code == 200, f"Complaint {idx} failed: {res.text}"
        data = res.json()
        print(f"[{idx:02d}] Text: {text[:45]:<45} -> Cat: {data['category']:<10} Loc: {data['location']:<12} Urg: {data['urgency']:<7} Lang: {data['language_detected']:<16} Added: +{data['complaints_added']}")

    # 4. Test POST /simulate
    print("\n--- Testing POST /simulate ---")
    res = requests.post(f"{BASE_URL}/simulate", json={"funded": ["Rampur", "Devnagar"]})
    assert res.status_code == 200, f"POST /simulate failed: {res.text}"
    sim_data = res.json()
    print(f"[OK] POST /simulate (Rampur, Devnagar): Current={sim_data['current_national_coverage']:.3f}, Projected={sim_data['projected_national_coverage']:.3f}, Gain=+{sim_data['gain']:.3f}")
    assert sim_data["gain"] > 0

    # Test simulate with empty funded list
    res_empty = requests.post(f"{BASE_URL}/simulate", json={"funded": []})
    assert res_empty.status_code == 200
    sim_empty = res_empty.json()
    print(f"[OK] POST /simulate (empty): Current={sim_empty['current_national_coverage']:.3f}, Gain=+{sim_empty['gain']:.3f}")
    assert sim_empty["gain"] == 0.0

    # 5. Test GET /impact
    print("\n--- Testing GET /impact ---")
    res = requests.get(f"{BASE_URL}/impact")
    assert res.status_code == 200, f"GET /impact failed: {res.text}"
    impact_data = res.json()
    print(f"[OK] GET /impact returned {len(impact_data.get('funded_districts', []))} funded districts with 6-month simulated trajectories.")
    for d in impact_data.get("funded_districts", []):
        m0 = d["trajectory"][0]["complaints"]
        m6 = d["trajectory"][-1]["complaints"]
        print(f"  - {d['name']} ({d['category']}): Month 0 = {m0} -> Month 6 = {m6} (Drop: {d['overall_drop_percentage']}%)")

    # 6. Test GET /trends
    print("\n--- Testing GET /trends ---")
    res = requests.get(f"{BASE_URL}/trends")
    assert res.status_code == 200, f"GET /trends failed: {res.text}"
    trends_data = res.json()
    print(f"[OK] GET /trends verified: Months={trends_data['trends']['months']}, Receipts len={len(trends_data['trends']['receipts'])}")

    # 7. Test GET /docs
    res = requests.get(f"{BASE_URL}/docs")
    assert res.status_code == 200, "GET /docs failed"
    print("[OK] GET /docs is accessible (FastAPI Swagger UI)")

    print("\n=== ALL BACKEND TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_all()
