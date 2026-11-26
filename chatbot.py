"""Context-aware AI Assistant for DRiShti-AI Studio (Groq, Gemini, OpenAI, and Offline fallback)."""

import json
import os
import urllib.error
import urllib.request


GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

DR_CLASS_GUIDE = {
    "No DR": "No visible signs of diabetic retinopathy detected. Continue annual screening and glycemic control.",
    "Mild": "Early microaneurysms may be present. Routine follow-up and diabetes care are recommended.",
    "Moderate": "More noticeable retinal blood-vessel changes are present. Priority ophthalmologist evaluation is recommended.",
    "Severe": "Extensive retinal lesions with high progression risk. Urgent specialist eye examination is strongly advised.",
    "Proliferative DR": "Advanced diabetic retinopathy with possible abnormal new vessels. Immediate ophthalmology referral is critical.",
}

SYSTEM_PROMPT = (
    "You are the DRiShti-AI Clinical Screening Assistant supporting health workers at rural "
    "primary health centers in India. Explain diabetic retinopathy screening outputs, retinal "
    "attention heatmaps, image quality checks, and referral urgency in clear, empathetic, "
    "practical language. If asked for Hindi, respond clearly in Hindi (Devanagari). "
    "Never diagnose or prescribe medication. Always remind users that DRiShti-AI is an AI-assisted "
    "screening prototype and Moderate, Severe, Proliferative DR, or poor-quality scans require "
    "specialist evaluation or recapture. Keep answers concise, structured, and actionable."
)


def build_anonymized_context(scan_result, clinical_notes=None):
    """Build a non-PII JSON context payload from the active scan and clinical intake."""
    if not scan_result and not clinical_notes:
        return None

    context = {}
    if clinical_notes:
        context["clinical_intake"] = {
            k: v for k, v in clinical_notes.items()
            if k not in ("patient_name", "patient_id") and v not in (None, "", [])
        }

    if scan_result:
        context.update({
            "predicted_class": scan_result.get("predicted_class"),
            "confidence_pct": scan_result.get("confidence_pct"),
            "all_probabilities_pct": scan_result.get("probabilities"),
            "image_quality_status": scan_result.get("image_quality_status"),
            "image_quality_pct": scan_result.get("image_quality_pct"),
            "reliability_status": scan_result.get("reliability_status"),
            "reliability_pct": scan_result.get("reliability_pct"),
            "referral_priority": scan_result.get("referral_priority"),
            "urgency_level": scan_result.get("urgency_level"),
            "recommended_action": scan_result.get("recommended_action"),
            "engine_mode": scan_result.get("engine_mode"),
        })

    return context or None


def _http_post_json(url, payload, headers=None, timeout=25):
    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "DRiShti-AI-Studio/1.0",
    }
    if headers:
        req_headers.update(headers)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {err.code}: {detail[:240]}") from err


def _format_system_context(context):
    if not context:
        return SYSTEM_PROMPT + "\n\nNo retinal scan has been analyzed in this session yet."
    return SYSTEM_PROMPT + "\n\nActive anonymized scan context:\n" + json.dumps(context, indent=2)


def _call_openai_compatible(url, messages, context, api_key, model):
    chat_messages = [{"role": "system", "content": _format_system_context(context)}]
    for m in messages[-10:]:
        chat_messages.append({"role": m["role"], "content": m["content"]})
    payload = {
        "model": model,
        "messages": chat_messages,
        "temperature": 0.3,
        "max_tokens": 700,
    }
    resp = _http_post_json(url, payload, headers={"Authorization": f"Bearer {api_key}"})
    return resp["choices"][0]["message"]["content"].strip()


def _call_gemini(messages, context, api_key, model="gemini-2.5-flash"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    contents = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in messages[-10:]
    ]
    payload = {
        "systemInstruction": {"parts": [{"text": _format_system_context(context)}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 700},
    }
    resp = _http_post_json(url, payload)
    parts = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def _offline_fallback_reply(prompt, context):
    text = (prompt or "").lower()
    has_scan = bool(context and context.get("predicted_class"))

    if "hindi" in text or "हिंदी" in text:
        if not has_scan:
            return (
                "**ऑफ़लाइन सहायक (Offline Assistant):**\n"
                "अभी कोई रेटिना स्कैन विश्लेषित नहीं हुआ है। कृपया **Screening Studio** में फंडस फोटो अपलोड कर "
                "**Analyze Retinal Image** दबाएं।\n\n"
                "_नोट: DRiShti-AI केवल प्रारंभिक जांच में सहायता के लिए है; अंतिम निदान नेत्र विशेषज्ञ से ही लें।_"
            )
        return (
            f"**वर्तमान जांच का सरल विवरण (Offline Mode):**\n"
            f"- **संभावित श्रेणी:** {context['predicted_class']} ({context['confidence_pct']}% विश्वास)\n"
            f"- **फोटो गुणवत्ता:** {context['image_quality_status']} ({context['image_quality_pct']}%)\n"
            f"- **रेफ़रल प्राथमिकता:** {context['referral_priority']} ({context['urgency_level']})\n"
            f"- **सुझाया गया कदम:** {context['recommended_action']}\n\n"
            "_नोट: यह AI-सहायता प्राप्त स्क्रीनिंग परिणाम है, अंतिम निर्णय नेत्र विशेषज्ञ से लें।_"
        )

    if "grad" in text or "heatmap" in text or "red" in text:
        return (
            "**Reading the Attention Heatmap:**\n"
            "- **Warm colors (red/yellow)** highlight retinal regions with stronger feature activation.\n"
            "- **Cool colors (blue)** indicate lower model attention.\n"
            "- Drag the **Split Compare Slider** or adjust **Opacity** and **Threshold** to verify vessels and lesions."
        )

    if "quality" in text or "blur" in text or "retake" in text:
        if has_scan:
            return (
                f"**Image Quality Check:** Status **{context['image_quality_status']}** "
                f"({context['image_quality_pct']}%). Reliability: **{context['reliability_pct']}%**.\n"
                "Retake in dim lighting if blur or glare is visible."
            )
        return "**Fundus Capture Tips:** Capture in dim lighting, keep the camera steady, and center the optic disc and macula."

    if "class" in text or "severity" in text or "stage" in text:
        return "**5 DR Severity Classes:**\n" + "\n".join(
            f"- **{k}:** {v}" for k, v in DR_CLASS_GUIDE.items()
        )

    if has_scan:
        cls = context["predicted_class"]
        return (
            f"**Screening Summary (Offline Assistant):**\n"
            f"- **Predicted Class:** {cls} ({context['confidence_pct']}%)\n"
            f"- **Meaning:** {DR_CLASS_GUIDE.get(cls, '')}\n"
            f"- **Image Quality:** {context['image_quality_status']} ({context['image_quality_pct']}%)\n"
            f"- **Referral:** {context['referral_priority']} ({context['urgency_level']})\n"
            f"- **Action:** {context['recommended_action']}"
        )

    return (
        "**Offline Screening Assistant:**\n"
        "Upload a fundus scan (or click a Demo button) in **Screening Studio**, or ask about DR severity classes, "
        "image quality guidelines, or Grad-CAM heatmaps."
    )


def generate_chat_reply(
    messages,
    scan_result=None,
    clinical_notes=None,
    connectivity="Online",
    provider="Auto",
    api_keys=None,
    groq_model="openai/gpt-oss-120b",
):
    """Return `(reply_text, backend_label)` using Groq, Gemini, OpenAI, or Offline fallback."""
    context = build_anonymized_context(scan_result, clinical_notes=clinical_notes)
    latest_prompt = messages[-1]["content"] if messages else ""
    keys = api_keys or {}

    groq_key = (keys.get("groq") or os.environ.get("GROQ_API_KEY", "")).strip()
    gemini_key = (keys.get("gemini") or os.environ.get("GEMINI_API_KEY", "")).strip()
    openai_key = (keys.get("openai") or os.environ.get("OPENAI_API_KEY", "")).strip()

    if connectivity != "Offline / Local":
        if provider in ("Auto", "Groq API") and groq_key:
            try:
                reply = _call_openai_compatible(
                    "https://api.groq.com/openai/v1/chat/completions",
                    messages,
                    context,
                    groq_key,
                    model=groq_model,
                )
                return reply, f"Groq ({groq_model})"
            except Exception as exc:
                fallback = _offline_fallback_reply(latest_prompt, context)
                return f"_Groq API unavailable ({exc}). Showing offline guidance:_\n\n{fallback}", "Offline Fallback"

        if provider in ("Auto", "Gemini API") and gemini_key:
            try:
                return _call_gemini(messages, context, gemini_key), "Gemini API"
            except Exception as exc:
                fallback = _offline_fallback_reply(latest_prompt, context)
                return f"_Gemini API unavailable ({exc}). Showing offline guidance:_\n\n{fallback}", "Offline Fallback"

        if provider in ("Auto", "OpenAI API") and openai_key:
            try:
                reply = _call_openai_compatible(
                    "https://api.openai.com/v1/chat/completions",
                    messages,
                    context,
                    openai_key,
                    model="gpt-4o-mini",
                )
                return reply, "OpenAI API"
            except Exception as exc:
                fallback = _offline_fallback_reply(latest_prompt, context)
                return f"_OpenAI API unavailable ({exc}). Showing offline guidance:_\n\n{fallback}", "Offline Fallback"

    return _offline_fallback_reply(latest_prompt, context), "Built-in Offline Assistant"
