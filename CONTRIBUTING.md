# Contributing to DRiShti-AI Studio

Thank you for collaborating on **DRiShti-AI Studio**! Follow this workflow so teammates and contributors can work cleanly on separate branches without breaking `main`.

## 1. Getting Started (Teammates vs. External Contributors)

- **If you are an added collaborator:** Clone the repo directly:
  ```bash
  git clone https://github.com/Abhay6969-boop/DRiShti-AI-Studio.git
  cd DRiShti-AI-Studio
  ```
- **If you are an external contributor:** Click **Fork** on GitHub, then clone your fork:
  ```bash
  git clone https://github.com/<your-username>/DRiShti-AI-Studio.git
  cd DRiShti-AI-Studio
  ```

## 2. Create a Feature Branch

Never commit experimental changes directly to `main`. Always branch from the latest `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/short-description
```

Suggested branch prefixes:
- `feature/...` — new UI or backend capabilities (e.g. `feature/hindi-voice-summary`)
- `fix/...` — bug fixes (e.g. `fix/csv-export-encoding`)
- `docs/...` — documentation updates

## 3. Local Environment Setup

```bash
cp .env.example .env
python -m pip install -r requirements.txt
python server.py
```

- **Never commit `.env`** or paste real API keys into code files.
- Check `git status` before every commit to confirm `.env` is not staged.

## 4. Commit, Push & Open a Pull Request

```bash
git status
git add .
git commit -m "Add: brief summary of your change"
git push -u origin feature/short-description
```

Then on GitHub:
1. Open the repository page and click **Compare & pull request**.
2. Describe what you changed and how you tested it (`python server.py`, browser check).
3. Request a review from a teammate before merging into `main`.
