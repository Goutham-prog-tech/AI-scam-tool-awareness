# AI Scam Awareness Tool

A bilingual (English / Telugu) web app that checks a suspicious message (typed, pasted, or read from screenshots) and shows which common scam warning signs it contains, why they are dangerous, and what to do next. It never says "100% scam": it reports *potential scam indicators* because no classifier is perfect.

## Features
- Weighted rule engine (English, Telugu, Hindi/Hinglish) + machine-learning score (TF-IDF + Logistic Regression)
- Messages up to 5000 characters; screenshots are read on the user's own device (OCR) and never uploaded
- Risk meter, reasons, recommended actions, and the national Cyber Crime Helpline (1930, cybercrime.gov.in)
- Voice assistant (English / Telugu / Hindi, male or female voice) that reads the warning aloud
- Language chooser, light / dark / high-contrast themes, text-size settings, 3D visual effects
- Security: strict Content-Security-Policy, security headers, rate limiting, input validation

## Run on your computer
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python train_model.py
python app.py
```
Then open http://127.0.0.1:5000

## Built-in male / female voices (optional, recommended)
Phones and laptops often have no Telugu voice, and many have only one voice. To get real male and female English / Telugu / Hindi voices on every device, run once on your computer (needs internet):
```
pip install edge-tts
python make_voice_clips.py
```
Then upload the generated `static/audio` folder to GitHub. Without it, the site uses the device's own voices.

## Deploy (Render)
- Build command: `pip install -r requirements.txt && python train_model.py`
- Start command: `gunicorn app:app`

## Project structure
| Path | Purpose |
|---|---|
| app.py | Flask server, routes, security headers, rate limiting |
| analyzer.py | Rule engine, scoring, language detection |
| train_model.py | Trains the ML model from data/messages.csv |
| templates/index.html | Web page (HTML + CSS + JavaScript) |
| static/ | Fonts and the in-browser OCR engine |
| ocr_lang/ | OCR language data (English, Telugu, Hindi) |

This tool is an awareness aid and can make mistakes. Always verify suspicious messages independently.
