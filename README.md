# 👁️ DRiShti-AI Studio

**Explainable Diabetic Retinopathy Screening & Groq-Powered Clinical Assistant for Rural Primary Health Centers (PHCs)**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-0f5c5c)
![AI](https://img.shields.io/badge/Assistant-Groq%20%2B%20Offline%20Fallback-5b4fcf)
![License](https://img.shields.io/badge/License-MIT-green)

> **Live Demo:** `https://your-render-url.onrender.com` *(Deploy on Render below and replace this link)*

---

## ✨ Key Features

- **🔍 Screening Studio:**
  - Patient & clinical intake (age, sex, eye screened `OS/OD`, diabetes duration, reported visual symptoms).
  - In-browser **Image Quality Gate** (brightness, contrast, sharpness) with poor-quality retake alerts.
  - Built-in **Healthy / Moderate / Severe** synthetic fundus demo generators for instant testing.
  - **4 Radial SVG Gauges** (AI Confidence, Image Quality, Model Trust, Final Reliability) + bilingual (**English / हिंदी**) patient guidance & health-worker triage checklist.
- **🔥 Interactive Split-Compare XAI Studio:**
  - Draggable **Split Curtain Compare** slider (Original Retina vs. Attention Heatmap), **Side-by-Side**, and **Overlay Only** modes.
  - Live **Colormap** (`JET`, `TURBO`, `HOT`, `INFERNO`), **Opacity**, and **Hotspot Threshold** controls.
- **💬 Groq AI Clinical Assistant (Online + Offline Fallback):**
  - Available both as a **floating chat drawer** and a dedicated **AI Assistant** tab.
  - Powered by **Groq** (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`) with Gemini/OpenAI support and a **Built-in Offline Assistant** (English & Hindi).
  - **Privacy-first:** Patient name and patient ID are stripped before sending scan context to external LLMs.
- **📊 Dashboard & 📋 History:**
  - Filterable analytics (KPIs, Severity Donut chart, Referral Priority bars), searchable history table, case inspector modal, printable PDF report (`Ctrl+P`), and CSV export.

---

## 🧠 5 Diabetic Retinopathy Severity Classes

| Class | Meaning | Typical Triage |
| :--- | :--- | :--- |
| **No DR** | No visible retinal damage | Routine annual screening |
| **Mild** | Early microaneurysms | Routine follow-up & glycemic care |
| **Moderate** | Noticeable blood-vessel changes | Priority specialist referral |
| **Severe** | Extensive retinal lesions | Urgent ophthalmology referral |
| **Proliferative DR** | Abnormal new blood vessels | Immediate specialist referral |

---

## 🗂️ Project Structure

```text
DRiShti-AI-Studio/
├── server.py                  # Flask server, screening API, history & CSV export
├── chatbot.py                 # Groq / Gemini / OpenAI + Offline assistant engine
├── templates/index.html       # Single-page clinical workbench UI
├── static/
│   ├── style.css              # Glassmorphic light/dark medical theme & print styles
│   └── app.js                 # Canvas pixel quality analyzer, split-compare XAI, chat UI
├── data/
│   └── screening_history.json # Local JSON persistence
├── .vscode/launch.json        # One-keypress F5 launch + auto-open browser in VS Code
├── Procfile                   # Production Gunicorn entrypoint for Render / Railway
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── CONTRIBUTING.md            # Team branching & Pull Request guide
└── LICENSE                    # MIT License
```

---

## 🚀 Run Locally in VS Code

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Abhay6969-boop/DRiShti-AI-Studio.git
   cd DRiShti-AI-Studio
   ```
2. **Configure your API key locally (optional — offline mode works without a key):**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and add your key from [Groq Console](https://console.groq.com/keys):
   ```env
   GROQ_API_KEY=gsk_your_key_here
   ```
   *(Never commit `.env` — it is ignored by `.gitignore`.)*
3. **Install dependencies:**
   ```bash
   python -m pip install -r requirements.txt
   ```
4. **Start the app:**
   - **In VS Code:** Press **`F5`** (automatically starts `server.py` and opens `http://127.0.0.1:5000`), **or**
   - **Terminal:**
     ```bash
     python server.py
     ```
     Then open `http://127.0.0.1:5000`.

---

## ☁️ Deploy Live (Free on Render)

1. Push your latest code to GitHub (`main` branch).
2. On [render.com](https://render.com), click **New + → Web Service** and connect `Abhay6969-boop/DRiShti-AI-Studio`.
3. Configure:
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn server:app --bind 0.0.0.0:$PORT`
4. Add an Environment Variable:
   - **Key:** `GROQ_API_KEY` | **Value:** your Groq API key
5. Deploy and paste your live `https://...onrender.com` link at the top of this README and in your GitHub repository **About → Website** field.

---

## 🤝 Contributing & Branching Workflow

Anyone is welcome to collaborate! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for our branching and Pull Request workflow:
- Keep `main` clean and deployable.
- Create a new branch for each feature or fix (`git checkout -b feature/your-feature`).
- Open a **Pull Request** on GitHub to merge changes into `main`.

---

## ⚠️ Disclaimer

DRiShti-AI Studio is an AI-assisted screening and triage prototype. It is **not** clinically validated and does not replace professional ophthalmological examination, clinical judgment, or diagnosis by a qualified doctor.
