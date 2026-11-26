"""Flask server and REST API for DRiShti-AI Studio."""

import base64
import csv
import io
import json
import math
import os
import sys
import tempfile
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request

from chatbot import GROQ_MODELS, generate_chat_reply

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "screening_history.json")
os.makedirs(DATA_DIR, exist_ok=True)


def load_dotenv_file(path):
    """Load key=value pairs from a local .env file without external dependencies."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


load_dotenv_file(os.path.join(BASE_DIR, ".env"))

# Optional TensorFlow EfficientNetB0 integration when host permits loading TF wheels.
TF_ENGINE = None
TF_ENGINE_ERROR = ""
CANDIDATE_MODEL_DIRS = [
    os.environ.get("DRISHTI_MODEL_DIR", ""),
    os.path.join(BASE_DIR, "DRiShti_AI_explanation"),
    os.path.join(os.path.dirname(BASE_DIR), "DRiShti-AI", "DRiShti_AI_explanation"),
]
for model_dir in CANDIDATE_MODEL_DIRS:
    if model_dir and os.path.isdir(model_dir):
        try:
            if model_dir not in sys.path:
                sys.path.insert(0, model_dir)
            from inference import DrishtiAI  # type: ignore

            TF_ENGINE = DrishtiAI(model_dir)
            break
        except Exception as exc:
            TF_ENGINE_ERROR = str(exc)

app = Flask(__name__)


def read_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def write_history(records):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def _compute_heuristic_screening(metrics, intake):
    """Quality + trust-aware heuristic screening when TensorFlow is unavailable on host."""
    brightness = float(metrics.get("brightness_score", 70))
    contrast = float(metrics.get("contrast_score", 70))
    sharpness = float(metrics.get("sharpness_score", 70))
    lesion_signal = float(metrics.get("lesion_signal", 0.25))
    exudate_signal = float(metrics.get("exudate_signal", 0.15))

    quality_pct = round(0.30 * brightness + 0.30 * contrast + 0.40 * sharpness, 1)
    quality_status = "GOOD" if quality_pct >= 75 else ("ACCEPTABLE" if quality_pct >= 50 else "POOR")

    duration_bonus = min(0.18, float(intake.get("diabetes_duration") or 0) * 0.01)
    symptom_bonus = min(0.22, len(intake.get("symptoms") or []) * 0.07)
    severity_index = max(0.0, min(1.0, 0.55 * lesion_signal + 0.35 * exudate_signal + duration_bonus + symptom_bonus))

    classes = ["No DR", "Mild", "Moderate", "Severe", "Proliferative DR"]
    centers = [0.12, 0.34, 0.56, 0.76, 0.92]
    logits = [math.exp(-((severity_index - c) ** 2) / 0.045) for c in centers]
    total = sum(logits)
    probs = {cls: round((val / total) * 100, 2) for cls, val in zip(classes, logits)}

    best_cls = max(probs, key=probs.get)
    sorted_vals = sorted(probs.values(), reverse=True)
    conf_pct = sorted_vals[0]
    margin_pct = round(sorted_vals[0] - sorted_vals[1], 2)

    probs_unit = [v / 100.0 for v in probs.values() if v > 0]
    entropy = -sum(p * math.log(p) for p in probs_unit) / math.log(len(classes))
    certainty_pct = round((1.0 - entropy) * 100, 1)

    model_trust_pct = round(0.50 * conf_pct + 0.25 * margin_pct + 0.25 * certainty_pct, 1)
    model_trust_status = "HIGH TRUST" if model_trust_pct >= 75 else ("MODERATE TRUST" if model_trust_pct >= 50 else "LOW TRUST")

    final_trust_pct = round(0.70 * model_trust_pct + 0.30 * quality_pct, 1)
    final_trust_status = "HIGH TRUST" if final_trust_pct >= 75 else ("MODERATE TRUST" if final_trust_pct >= 50 else "LOW TRUST")

    if final_trust_status == "LOW TRUST":
        referral = ("SPECIALIST REVIEW REQUIRED", "UNCERTAIN", "Do not rely solely on automated output; refer for ophthalmologist review.")
    elif quality_status == "POOR":
        referral = ("RETAKE IMAGE / REVIEW", "IMAGE QUALITY ISSUE", "Capture a clearer, evenly lit retinal photograph before triage.")
    elif best_cls == "No DR":
        referral = ("ROUTINE SCREENING", "LOW", "Continue annual diabetic eye screening and blood-sugar monitoring.")
    elif best_cls == "Mild":
        referral = ("ROUTINE REFERRAL", "LOW-MODERATE", "Schedule a routine ophthalmology check and reinforce glycemic control.")
    elif best_cls == "Moderate":
        referral = ("PRIORITY REFERRAL", "MODERATE", "Schedule specialist ophthalmic evaluation within the priority window.")
    elif best_cls == "Severe":
        referral = ("URGENT REFERRAL", "HIGH", "Refer promptly to an ophthalmologist to prevent progression.")
    else:
        referral = ("URGENT REFERRAL", "VERY HIGH", "Immediate ophthalmology referral required for advanced retinal changes.")

    return {
        "engine_mode": "Local Image-Quality & Triage Heuristic (TensorFlow blocked/unavailable on host)",
        "predicted_class": best_cls,
        "confidence_pct": round(conf_pct, 1),
        "margin_pct": round(margin_pct, 1),
        "entropy": round(entropy, 3),
        "probabilities": probs,
        "image_quality_status": quality_status,
        "image_quality_pct": quality_pct,
        "quality_breakdown": {
            "brightness": round(brightness, 1),
            "contrast": round(contrast, 1),
            "sharpness": round(sharpness, 1),
        },
        "model_trust_status": model_trust_status,
        "model_trust_pct": model_trust_pct,
        "reliability_status": final_trust_status,
        "reliability_pct": final_trust_pct,
        "referral_priority": referral[0],
        "urgency_level": referral[1],
        "recommended_action": referral[2],
        "gradcam_grid": metrics.get("attention_grid"),
    }


@app.route("/")
def index():
    return render_template("index.html", groq_models=GROQ_MODELS)


@app.route("/api/health", methods=["GET"])
def health():
    records = read_history()
    urgent = sum(1 for r in records if "URGENT" in str(r.get("referral_priority", "")).upper())
    return jsonify({
        "status": "ok",
        "tf_loaded": TF_ENGINE is not None,
        "tf_note": "EfficientNetB0 Loaded" if TF_ENGINE else (TF_ENGINE_ERROR or "Heuristic Mode Active"),
        "groq_configured": bool(os.environ.get("GROQ_API_KEY", "").strip()),
        "groq_models": GROQ_MODELS,
        "total_records": len(records),
        "urgent_records": urgent,
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}
    intake = payload.get("intake") or {}
    metrics = payload.get("image_metrics") or {}
    image_b64 = payload.get("image_base64", "")

    if TF_ENGINE is not None and image_b64:
        try:
            encoded = image_b64.split(",", 1)[-1]
            img_bytes = base64.b64decode(encoded)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name
            try:
                res = TF_ENGINE.analyze(tmp_path, generate_gradcam=True)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            pred = res["prediction"]
            qual = res["image_quality"]
            unc = res["uncertainty"]
            mt = res["model_trust"]
            ft = res["final_trust"]
            ref = res["referral"]
            heatmap = res.get("gradcam_heatmap")
            grid = heatmap.tolist() if heatmap is not None else metrics.get("attention_grid")

            return jsonify({
                "engine_mode": "EfficientNetB0 + Grad-CAM",
                "predicted_class": pred["class_name"],
                "confidence_pct": round(pred["confidence"] * 100, 1),
                "margin_pct": round(unc["margin"] * 100, 1),
                "entropy": round(unc["entropy"], 3),
                "probabilities": {k: round(v * 100, 2) for k, v in pred["all_probabilities"].items()},
                "image_quality_status": qual["status"],
                "image_quality_pct": round(qual["percentage"], 1),
                "quality_breakdown": {
                    "brightness": round(qual["brightness_score"], 1),
                    "contrast": round(qual["contrast_score"], 1),
                    "sharpness": round(qual["sharpness_score"], 1),
                },
                "model_trust_status": mt["status"],
                "model_trust_pct": round(mt["percentage"], 1),
                "reliability_status": ft["status"],
                "reliability_pct": round(ft["percentage"], 1),
                "referral_priority": ref["priority"],
                "urgency_level": ref["urgency_level"],
                "recommended_action": ref["action"],
                "gradcam_grid": grid,
            })
        except Exception:
            pass

    return jsonify(_compute_heuristic_screening(metrics, intake))


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages") or []
    scan_result = payload.get("scan_result")
    clinical_notes = payload.get("clinical_notes")
    connectivity = payload.get("connectivity", "Online")
    provider = payload.get("provider", "Auto")
    groq_model = payload.get("groq_model", GROQ_MODELS[0])
    custom_key = payload.get("api_key", "")

    api_keys = {
        "groq": custom_key if provider in ("Auto", "Groq API") and custom_key else os.environ.get("GROQ_API_KEY", ""),
        "gemini": custom_key if provider == "Gemini API" and custom_key else os.environ.get("GEMINI_API_KEY", ""),
        "openai": custom_key if provider == "OpenAI API" and custom_key else os.environ.get("OPENAI_API_KEY", ""),
    }

    reply, backend = generate_chat_reply(
        messages=messages,
        scan_result=scan_result,
        clinical_notes=clinical_notes,
        connectivity=connectivity,
        provider=provider,
        api_keys=api_keys,
        groq_model=groq_model,
    )
    return jsonify({"reply": reply, "backend": backend})


@app.route("/api/history", methods=["GET", "POST", "DELETE"])
def history():
    if request.method == "GET":
        return jsonify({"records": list(reversed(read_history()))})

    if request.method == "POST":
        record = request.get_json(silent=True) or {}
        record.setdefault("timestamp", datetime.now().isoformat())
        records = read_history()
        records.append(record)
        write_history(records)
        return jsonify({"saved": True, "total": len(records)})

    write_history([])
    return jsonify({"cleared": True})


@app.route("/api/history/export", methods=["GET"])
def export_history():
    records = read_history()
    output = io.StringIO()
    fields = [
        "timestamp", "patient_name", "patient_id", "age", "sex", "eye_side",
        "diabetes_duration", "predicted_class", "confidence_pct",
        "image_quality_status", "reliability_pct", "referral_priority",
        "urgency_level", "connectivity",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in records:
        writer.writerow(row)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=drishti_ai_history.csv"},
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
