"""
NLU Classifier for citizen infrastructure grievances.
Two-layer approach:
  Layer A: Offline Keyword Classifier (always available, handles English, Romanized Hindi, Punjabi, Mixed)
  Layer B: Optional Gemini API (google-generativeai) fallback with silent failover
In-memory caching for sub-millisecond repeated analysis.
"""

import os
import re
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# In-memory NLU cache
_NLU_CACHE: Dict[str, Dict[str, Any]] = {}

DISTRICT_NAMES = [
    "Rampur",
    "Bharatpur",
    "Sundargram",
    "Kotwali",
    "Devnagar",
    "Anantpur",
    "Nirmalpur",
    "Vasant Vihar",
    "Chandanpur"
]

CATEGORIES = ["Water", "Roads", "Power", "Sanitation", "Health", "General"]

# Keyword dictionaries for multilingual support
KEYWORDS_CATEGORY = {
    "Water": [
        "water", "paani", "pani", "jal", "pipe", "pipeline", "tap", "null", "nal",
        "boring", "tubewell", "handpump", "tanker", "leakage", "dirty water",
        "peene ka paani", "sewage water", "water supply", "shortage", "dry tap",
        "contamination", "ganda pani", "paani nahi", "pani di samasya"
    ],
    "Roads": [
        "road", "sadak", "pothole", "khadda", "gaddha", "khadde", "rasta",
        "bridge", "pul", "puliya", "highway", "tar", "tarmac", "street",
        "flyover", "broken road", "tuti sadak", "sadak kharab", "accident prone",
        "muddy road", "sadak tuti"
    ],
    "Power": [
        "power", "electricity", "bijli", "current", "light", "voltage",
        "transformer", "wire", "taar", "outage", "blackout", "load shedding",
        "meter", "pole", "khamba", "bijli cut", "bijli gul", "no power",
        "power cut", "sparking", "low voltage"
    ],
    "Sanitation": [
        "sanitation", "waste", "kachra", "garbage", "sewer", "sewerage",
        "naali", "nali", "drain", "drainage", "gutter", "safai", "cleanliness",
        "dumping", "dustbin", "overflow", "badbu", "stench", "toilet",
        "shauchalaya", "stinking", "filth", "kachra dump"
    ],
    "Health": [
        "health", "hospital", "aspatal", "doctor", "nurse", "medicine",
        "dawai", "dawa", "clinic", "phc", "ambulance", "fever", "illness",
        "bimari", "treatment", "ilaaj", "dispensary", "vaccine", "icu",
        "patient", "operation", "bed", "medical"
    ]
}

KEYWORDS_URGENT = [
    "urgent", "emergency", "khatra", "danger", "dangerous", "critical",
    "death", "died", "fatal", "immediate", "turant", "jaldi", "collapse",
    "bleeding", "severe", "disaster", "blast", "electrocution", "epidemic",
    "risk", "hazardous", "life threatening", "sos", "hazard", "mar gaye",
    "jaan ko khatra", "aag lag gayi", "jaldi karo"
]

KEYWORDS_HINDI_ROMANIZED = [
    "hai", "hain", "ho", "raha", "rahi", "rahe", "nahi", "nahin", "bahut",
    "bohot", "kharab", "samasya", "gaon", "turant", "kripya", "karo", "kijiye",
    "par", "me", "mein", "ka", "ki", "ke", "se", "ko", "kya", "kyun", "kyu",
    "hum", "log", "yahan", "wahan", "paani", "bijli", "sadak", "naali", "aspatal"
]

KEYWORDS_PUNJABI = [
    "vich", "pind", "hor", "karda", "kardi", "karde", "sanu", "ditta",
    "tuhada", "sade", "saade", "utte", "naal", "chahida", "hoya", "pani di"
]


def detect_location(text_lower: str) -> str:
    """Find matching district name from text."""
    # Check multi-word districts first
    if "vasant vihar" in text_lower or "vasantvihar" in text_lower:
        return "Vasant Vihar"
    if "dev nagar" in text_lower or "devnagar" in text_lower:
        return "Devnagar"

    for d in DISTRICT_NAMES:
        # Match as distinct word or token
        pattern = r"\b" + re.escape(d.lower()) + r"\b"
        if re.search(pattern, text_lower):
            return d

    # Substring fallback
    for d in DISTRICT_NAMES:
        if d.lower() in text_lower:
            return d

    return "Unknown"


def detect_urgency(text_lower: str) -> str:
    """Detect if request is Urgent or Normal."""
    for kw in KEYWORDS_URGENT:
        if kw in text_lower:
            return "Urgent"
    return "Normal"


def detect_language(text: str) -> str:
    """Detect primary language of complaint."""
    text_lower = text.lower()
    punjabi_score = sum(1 for kw in KEYWORDS_PUNJABI if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
    hindi_score = sum(1 for kw in KEYWORDS_HINDI_ROMANIZED if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
    english_words = re.findall(r"\b[a-zA-Z]+\b", text_lower)

    if punjabi_score >= 1:
        return "Punjabi"
    if hindi_score >= 2:
        return "Hindi (Romanized)"
    if hindi_score == 1 and len(english_words) > 4:
        return "Mixed"
    return "English"


def detect_category(text_lower: str) -> str:
    """Classify into one of 6 core infrastructure categories."""
    scores = {cat: 0 for cat in CATEGORIES}

    for cat, keywords in KEYWORDS_CATEGORY.items():
        for kw in keywords:
            if kw in text_lower:
                # Give higher weight to multi-word specific phrases
                weight = 3 if " " in kw else 1
                scores[cat] += weight

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        return best_cat
    return "General"


def classify_offline(text: str) -> Dict[str, Any]:
    """Offline keyword-based classification engine."""
    text_clean = text.strip()
    if not text_clean:
        return {
            "category": "General",
            "location": "Unknown",
            "urgency": "Normal",
            "language_detected": "English"
        }

    text_lower = text_clean.lower()
    return {
        "category": detect_category(text_lower),
        "location": detect_location(text_lower),
        "urgency": detect_urgency(text_lower),
        "language_detected": detect_language(text_clean)
    }


def try_gemini_classification(text: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Optional Layer B: Attempt Gemini API classification with modern google.genai and strict fallback."""
    try:
        raw = None
        prompt = f"""You are an AI civic grievance classifier for India's Setu infrastructure platform.
Analyze this citizen message and extract structured JSON with these exact keys:
- "category": Must be one of ["Water", "Roads", "Power", "Sanitation", "Health", "General"]
- "location": Exact matching district from this list: {DISTRICT_NAMES} or "Unknown"
- "urgency": "Urgent" or "Normal"
- "language_detected": e.g. "English", "Hindi (Romanized)", "Punjabi", "Mixed", or other regional Indian language

Citizen Message: "{text}"

Respond with ONLY valid JSON:"""

        try:
            # Modern google-genai SDK
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw = response.text.strip() if response and response.text else None
        except Exception:
            # Fallback to legacy google.generativeai if needed
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=api_key)
                model = legacy_genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt, request_options={"timeout": 6.0})
                raw = response.text.strip() if response and response.text else None
            except Exception:
                return None

        if not raw:
            return None

        # Clean markdown codeblocks if any
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw)
            raw = re.sub(r"```$", "", raw).strip()
            
        data = json.loads(raw)
        
        # Validate output shape
        cat = data.get("category", "General")
        if cat not in CATEGORIES:
            cat = "General"
            
        loc = data.get("location", "Unknown")
        if loc not in DISTRICT_NAMES and loc != "Unknown":
            loc = detect_location(text.lower())
            
        urgency = "Urgent" if str(data.get("urgency", "")).lower() == "urgent" else "Normal"
        lang = str(data.get("language_detected", "English"))
        
        return {
            "category": cat,
            "location": loc,
            "urgency": urgency,
            "language_detected": lang
        }
    except Exception:
        # Silent fallback to keyword classifier as required
        return None


def analyze_complaint(text: str) -> Dict[str, Any]:
    """
    Main entrypoint for NLU classification.
    Checks in-memory cache first, then attempts Gemini if key present,
    otherwise falls back reliably to offline keyword classifier.
    """
    cache_key = text.strip().lower()
    if cache_key in _NLU_CACHE:
        return _NLU_CACHE[cache_key].copy()

    # Step 1: Base keyword classification
    result = classify_offline(text)

    # Step 2: Try Gemini if API key is provided in .env / environment
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key and api_key != "your_gemini_api_key_here":
        gemini_result = try_gemini_classification(text, api_key)
        if gemini_result:
            result = gemini_result

    # Cache result
    _NLU_CACHE[cache_key] = result
    return result.copy()


def analyze_audio_complaint(file_bytes: bytes, mime_type: str = "audio/mp3") -> Dict[str, Any]:
    """
    Multimodal audio grievance classifier.
    Uses Gemini 2.5 Flash native audio comprehension to transcribe vernacular voice notes
    and classify category, district, and urgency.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return {
            "transcribed_text": "(Audio processing requires GEMINI_API_KEY in .env)",
            "category": "General",
            "location": "Unknown",
            "urgency": "Normal",
            "language_detected": "Audio (Offline Fallback)"
        }

    try:
        prompt = f"""You are an AI civic grievance classifier for India's Setu infrastructure platform.
Listen carefully to this citizen voice recording and extract structured JSON with these exact keys:
- "transcribed_text": Verbatim or translated transcription of what the citizen said
- "category": Must be one of ["Water", "Roads", "Power", "Sanitation", "Health", "General"]
- "location": Exact matching district from this list: {DISTRICT_NAMES} or "Unknown"
- "urgency": "Urgent" or "Normal"
- "language_detected": e.g. "Hindi", "Punjabi", "English", "Bhojpuri", "Mixed", etc.

Respond with ONLY valid JSON:"""

        raw = None
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            audio_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[audio_part, prompt]
            )
            raw = response.text.strip() if response and response.text else None
        except Exception:
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=api_key)
                model = legacy_genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(
                    [
                        {"mime_type": mime_type, "data": file_bytes},
                        prompt
                    ]
                )
                raw = response.text.strip() if response and response.text else None
            except Exception:
                raw = None

        if not raw:
            raise ValueError("Empty response from model")

        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw)
            raw = re.sub(r"```$", "", raw).strip()

        data = json.loads(raw)
        cat = data.get("category", "General")
        if cat not in CATEGORIES:
            cat = "General"

        loc = data.get("location", "Unknown")
        if loc not in DISTRICT_NAMES and loc != "Unknown":
            loc = detect_location(str(data.get("transcribed_text", "")).lower())

        urgency = "Urgent" if str(data.get("urgency", "")).lower() == "urgent" else "Normal"
        lang = str(data.get("language_detected", "Audio"))
        transcribed = str(data.get("transcribed_text", "Voice grievance captured.")).strip()

        return {
            "transcribed_text": transcribed,
            "category": cat,
            "location": loc,
            "urgency": urgency,
            "language_detected": lang
        }
    except Exception:
        return {
            "transcribed_text": "(Audio processing failed or format unsupported)",
            "category": "General",
            "location": "Unknown",
            "urgency": "Normal",
            "language_detected": "Audio Error"
        }

