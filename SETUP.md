# 💼 Wealth Management Simulator — Setup Guide

## What You're Building
An interactive financial advisory simulator where you practice managing a client's portfolio
through real market scenarios. Built with Python + Streamlit + Claude AI.

---

## Step 1: Install Python

1. Go to https://www.python.org/downloads/
2. Click the big yellow "Download Python 3.12.x" button
3. Run the installer
4. ⚠️ IMPORTANT: On the first screen, check the box that says "Add Python to PATH"
5. Click "Install Now"
6. When done, open a new Terminal (or Command Prompt on Windows) and type:
   ```
   python --version
   ```
   You should see something like: `Python 3.12.3`

---

## Step 2: Get an Anthropic API Key (for the AI features)

1. Go to https://console.anthropic.com
2. Sign up for an account
3. Go to "API Keys" in the left sidebar
4. Click "Create Key" and copy it (it looks like: sk-ant-api03-...)
5. Keep this safe — treat it like a password

---

## Step 3: Set Your API Key

### On Mac:
Open Terminal and type (replace the key with yours):
```
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

### On Windows:
Open Command Prompt and type:
```
set ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

---

## Step 4: Install the Required Packages

In Terminal/Command Prompt, navigate to your project folder:
```
cd path/to/wealth_simulator
```

Then install everything:
```
pip install -r requirements.txt
```

This installs:
- streamlit (the web app framework)
- anthropic (the AI library)
- numpy (math/numbers library)

---

## Step 5: Run the Simulator

```
streamlit run app.py
```

Your browser will automatically open to http://localhost:8501
The simulator will be running!

---

## File Structure Explained

```
wealth_simulator/
├── simulator.py     ← The "brain" — all game logic, math, and rules
├── app.py           ← The "face" — everything the user sees (UI)
├── requirements.txt ← List of packages needed
└── SETUP.md         ← This file
```

**Why two files?**
This is called "separation of concerns" — a real software engineering principle.
- simulator.py contains the rules and logic (could be reused in a mobile app, API, etc.)
- app.py is just one way to display it
This is how professional engineers structure projects.

---

## How the AI Integration Works

The simulator uses Claude AI (the same AI you're talking to right now) to:

1. **Generate client messages** — instead of picking from 5 hardcoded responses,
   Claude reads the full situation (market regime, client personality, anxiety level,
   portfolio performance) and writes a unique, realistic message every single turn.

2. **Generate market commentary** — after each market event, Claude explains
   WHY that market condition happens in the real world and how advisors respond.
   This turns the simulator into a genuine learning tool.

The AI context includes:
- Client name, goal, risk tolerance
- Current anxiety and trust levels
- Portfolio performance this period
- Market regime and description
- Turn number (relationship history)

---

## Concepts You're Learning

**Behavioral Finance:**
- Loss aversion (people feel losses ~2x more than equivalent gains)
- Recency bias (overweighting recent events)
- Control preference (wanting to make their own decisions)

**Wealth Management:**
- Asset allocation (stocks/bonds/cash balance)
- Risk tolerance matching
- Portfolio rebalancing

**Advisor Skills:**
- Communication during downturns
- Managing client anxiety vs. investment discipline
- When to accommodate client preferences vs. hold firm

**Software Engineering:**
- Separation of concerns (simulator.py vs app.py)
- State management (session_state)
- API integration (Anthropic SDK)
- Python classes and functions

---

## Troubleshooting

**"streamlit is not recognized"**
→ Python wasn't added to PATH during install. Reinstall Python and check the PATH box.

**"anthropic.APIError" or client messages say "fallback"**
→ Your API key isn't set. Redo Step 3.

**Port already in use**
→ Run: `streamlit run app.py --server.port 8502`

---

## For Your College Application / Resume

**Project Title:** Wealth Management Behavioral Simulator

**Description:**
Designed and built an AI-powered financial advisory simulator modeling investor psychology,
portfolio management, and advisor communication across multi-period market scenarios.
Built with Python, Streamlit, and Claude AI API integration.

**Skills demonstrated:** Python, API integration, behavioral finance, UI/UX design,
software architecture, financial modeling
