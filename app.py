"""
app.py — The Visual Interface
==============================
This file handles everything the USER SEES.
It imports the game logic from simulator.py and displays it nicely.

Run with:  streamlit run app.py
"""

import streamlit as st
import os
import json
from groq import Groq

# Import everything from our game engine
from simulator import (
    Client,
    generate_market_turn,
    calculate_portfolio_return,
    apply_recommendation,
    calculate_full_turn_deltas,
    get_scenario_context,
    calculate_career_score,
    get_career_title,
    generate_performance_feedback,
    COMM_STYLE_EFFECTS,
    RECOMMENDATION_EFFECTS,
    fmt_pct,
    clamp,
)


# ─────────────────────────────────────────────
# AI CLIENT MESSAGE GENERATOR
# ─────────────────────────────────────────────

def generate_client_message_ai(context):
    """
    Uses Groq (Llama 3) to generate a realistic, personalized client message.

    PROMPT ENGINEERING LESSON:
    The quality of AI output is almost entirely determined by prompt quality.
    Key techniques used here:
    - Give the AI a specific personality, not just a role
    - Provide concrete emotional context with numbers
    - Give examples of what NOT to do
    - Add a "temperature hint" by telling it to be unpredictable
    - Use a system message (role: system) to set behavior separately from the request
    """
    try:
        groq_client = Groq()

        # SYSTEM MESSAGE — sets the AI's overall behavior and personality
        # This is separate from the actual request (user message below)
        system_msg = f"""You are {context['client_name']}, a real person with money invested with a financial advisor.
You have a specific personality:
- You are {'very anxious and emotional' if context['anxiety'] > 70 else 'moderately concerned' if context['anxiety'] > 45 else 'calm and rational'} about money
- Your trust in your advisor is {'high — you generally believe in them' if context['trust'] > 65 else 'moderate — you want reassurance' if context['trust'] > 40 else 'low — you are skeptical of their advice'}
- You speak casually, like a real person texting or emailing
- You NEVER sound like a financial textbook
- You vary your sentence structure and word choice every single time
- You sometimes ramble, ask multiple questions, or express contradictory feelings — like real people do"""

        # USER MESSAGE — the specific situation this turn
        user_msg = f"""Write your message to your financial advisor RIGHT NOW.

The situation:
- It's check-in #{context['turn_number']} of your relationship
- The market just had a {context['regime']} period
- Your portfolio {context['portfolio_value_direction']} {context['portfolio_return_pct']}
- You are saving for: {context['client_goal']}
- Your risk tolerance is {context['risk_tolerance']}
- Your anxiety right now: {context['anxiety']}/100
- Your current mood: {context['intent_description']}

Rules:
- 2-4 sentences MAX
- No greetings like "Hi" or "Dear"
- No financial jargon unless you're sarcastically repeating something your advisor said
- Reference your specific goal ({context['client_goal']}) naturally
- Show your actual emotion — don't be polite if you're scared
- NEVER start with "I wanted to" or "I'm reaching out" — those are corporate phrases
- Make it sound completely different from a generic financial message

Write ONLY the message. Nothing else."""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            temperature=0.9,  # higher = more creative/varied (0=robotic, 1=creative)
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return _fallback_client_message(context)


def _fallback_client_message(context):
    """
    Simple fallback messages if the AI is unavailable.
    Better than crashing the app.
    """
    intent = context["intent"]
    name   = context["client_name"]
    goal   = context["client_goal"]
    ret    = context["portfolio_return_pct"]

    messages = {
        "override_threat":   f"{name}: I've had enough. The portfolio is down and I want to move everything to cash right now. I don't care what the plan says.",
        "panic":             f"{name}: We're down {ret} and I'm seeing terrible news everywhere. I'm seriously questioning whether we should change our approach. My {goal} is at risk.",
        "concerned":         f"{name}: I noticed we're down {ret} this period. Can you help me understand what's happening and whether our strategy for {goal} still makes sense?",
        "greedy":            f"{name}: Great period! We're up {ret}. I've been reading that the market is really strong right now — should we be putting more into stocks to take advantage?",
        "confident_checkin": f"{name}: Just checking in — things have been looking solid. Are we still on track for {goal}?",
        "neutral_checkin":   f"{name}: How are we doing this period? Any updates I should know about?",
    }
    return messages.get(intent, f"{name}: How are we looking this period?")


def grade_free_text_ai(user_text, context, intent):
    """
    Uses Groq to grade the advisor's free text response.

    PROMPT ENGINEERING LESSON:
    We ask the AI to return structured JSON instead of a paragraph.
    This is called structured output — we tell the AI exactly what format
    we want so we can parse and use it reliably in our code.

    FINANCE LESSON:
    The four dimensions we grade (empathy, clarity, alignment, professionalism)
    are the same ones real advisory firms use to evaluate client communication.
    Companies like Merrill Lynch actually score recorded advisor calls on
    these exact criteria — it's called a communication rubric.
    """
    if not user_text or len(user_text.strip()) < 10:
        return None  # don't grade if they barely wrote anything

    try:
        import json
        groq_client = Groq()

        prompt = f"""You are evaluating a financial advisor's written response to a client.

CLIENT SITUATION:
- Client name: {context['client_name']}
- Client goal: {context['client_goal']}
- Market this period: {context['regime']} — portfolio {context['portfolio_value_direction']} {context['portfolio_return_pct']}
- Client emotional state: {context['intent_description']}
- Client anxiety: {context['anxiety']}/100

ADVISOR'S RESPONSE:
"{user_text}"

Grade this response on four dimensions, each scored -2 to +2:
- empathy: Did they acknowledge the client's feelings? (-2=dismissive, 0=neutral, +2=excellent)
- clarity: Did they explain what's happening clearly? (-2=confusing, 0=neutral, +2=very clear)
- alignment: Did they reference the client's specific goal ({context['client_goal']})? (-2=ignored goal, 0=neutral, +2=directly addressed)
- professionalism: Was the tone appropriate? (-2=unprofessional, 0=neutral, +2=very professional)

Also write one sentence of specific coaching feedback.

Respond ONLY with valid JSON in exactly this format, nothing else:
{{"empathy": 0, "clarity": 0, "alignment": 0, "professionalism": 0, "feedback": "your feedback here"}}"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code blocks if model wraps in them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        grades = json.loads(raw)

        for k in ["empathy", "clarity", "alignment", "professionalism"]:
            grades[k] = clamp(int(grades[k]), -2, 2)

        total = grades["empathy"] + grades["clarity"] + grades["alignment"] + grades["professionalism"]
        grades["d_trust"]        = clamp(int(total * 0.8), -6, 6)
        grades["d_anxiety"]      = clamp(int(-total * 0.6), -5, 5)
        grades["d_satisfaction"] = clamp(int(total * 0.5), -4, 4)

        return grades

    except Exception:
        return None


def generate_market_commentary_ai(market, portfolio_return, client_name):
    """
    Uses Groq to generate a brief educational market commentary each turn.
    Teaches the user what's happening in the market and why.
    """
    try:
        groq_client = Groq()

        prompt = f"""You are a sharp, conversational finance professor explaining a market event to a smart student who is new to investing.

What just happened: {market['regime']} — {market['description']}
Portfolio result: {fmt_pct(portfolio_return)} this period

Write exactly 2 sentences:
1. A real-world explanation of WHY this market condition happens — reference something concrete like interest rates, corporate earnings, inflation, investor sentiment, or a historical parallel
2. One specific thing a skilled wealth manager does differently than an average one in this environment

Tone: Smart but plain English. No bullet points. No fluff. Make it genuinely interesting and educational — something the student would actually remember.
Write ONLY the 2 sentences. Nothing else."""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return f"Market conditions resulted in a {fmt_pct(portfolio_return)} portfolio return this period."


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Wealth Management Simulator",
    page_icon="💼",
    layout="wide",
)

# Custom CSS for cleaner look
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e2e;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
    }
    .feedback-good { color: #4CAF50; font-weight: bold; }
    .feedback-bad  { color: #f44336; font-weight: bold; }
    .feedback-neutral { color: #FFC107; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────
# st.session_state is how Streamlit "remembers" things between interactions.
# Without this, every button click would reset everything to zero.

def init_game():
    """Set up a fresh game session."""
    client = Client()
    market = generate_market_turn()
    port_return = calculate_portfolio_return(client.portfolio, market)
    context = get_scenario_context(client, market, port_return, 1)

    st.session_state.client            = client
    st.session_state.turn              = 1
    st.session_state.portfolio_value   = 100_000.0
    st.session_state.log               = []
    st.session_state.market            = market
    st.session_state.portfolio_return  = port_return
    st.session_state.context           = context
    st.session_state.client_message    = generate_client_message_ai(context)
    st.session_state.market_commentary = generate_market_commentary_ai(market, port_return, client.name)
    st.session_state.submitted         = False
    st.session_state.last_feedback     = None
    st.session_state.game_over         = False
    st.session_state.started           = False
    st.session_state.mode              = None  # "learning" or "simulation"


if "client" not in st.session_state:
    init_game()


# ─────────────────────────────────────────────
# INTRO / SPLASH SCREEN
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# INTRO / MODE SELECTION SCREEN
# ─────────────────────────────────────────────

if not st.session_state.started:
    st.title("💼 Wealth Management Simulator")
    st.markdown("#### AI-powered financial advisory training")
    st.markdown("---")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("### 📘 Learning Mode")
        st.markdown("""
        Best for: **Beginners & students**

        - Clean, simple layout
        - Key info highlighted, clutter removed
        - Tooltips explain every finance term
        - Guided prompts help you respond
        - Focus on understanding concepts
        """)
        if st.button("Start Learning Mode", use_container_width=True, type="primary"):
            st.session_state.mode    = "learning"
            st.session_state.started = True
            st.rerun()

    with col2:
        st.markdown("### 📈 Simulation Mode")
        st.markdown("""
        Best for: **Realistic practice**

        - Full advisor dashboard
        - Detailed market data and metrics
        - Quick Turn or Full Turn each round
        - AI grades your written responses
        - Mirrors real wealth management
        """)
        if st.button("Start Simulation Mode", use_container_width=True):
            st.session_state.mode    = "simulation"
            st.session_state.started = True
            st.rerun()

    st.markdown("---")
    st.caption("Built with Python, Streamlit, and Groq AI · Behavioral Finance Simulator v2.0")
    st.stop()


# ─────────────────────────────────────────────
# GAME OVER SCREEN
# ─────────────────────────────────────────────

if st.session_state.game_over:
    client      = st.session_state.client
    log         = st.session_state.log
    final_value = st.session_state.portfolio_value
    turns       = len(log)

    # ── Calculate Scores ──
    final_score, breakdown = calculate_career_score(log, client, final_value)
    title, title_desc      = get_career_title(final_score)
    feedback               = generate_performance_feedback(breakdown, client, log)

    # ── Header ──
    st.title("📊 Career Performance Report")
    st.markdown(f"## {title}")
    st.caption(title_desc)

    score_col, spacer = st.columns([1, 2])
    with score_col:
        st.metric("Overall Score", f"{final_score} / 100")
        st.progress(final_score / 100)

    st.markdown("---")

    # ── Four Score Components ──
    st.subheader("📐 Score Breakdown")
    st.caption("How your final score was calculated (with weights)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio Performance",  f"{breakdown['portfolio_score']}/100",
              help="Did the client's money grow vs. benchmark? (25% of score)")
    c2.metric("Client Relationship",    f"{breakdown['relationship_score']}/100",
              help="Trust + Satisfaction + low Anxiety + Engagement (35% of score)")
    c3.metric("Risk Management",        f"{breakdown['risk_score']}/100",
              help="Consistency — avoiding panic moves (25% of score)")
    c4.metric("Crisis Handling",        f"{breakdown['crisis_score']}/100",
              help="Communication during bear markets and crises (15% of score)")

    st.markdown("---")

    # ── Portfolio Results ──
    st.subheader("💰 Portfolio Results")
    gain_loss = final_value - 100_000
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Starting Value", "$100,000")
    p2.metric("Final Value",    f"${final_value:,.0f}", delta=f"${gain_loss:,.0f}")
    p3.metric("Your Return",    f"{breakdown['total_return_pct']}%")
    p4.metric("Benchmark",      f"{breakdown['benchmark_pct']}%",
              help="Simple 5%/year benchmark. Real advisors are compared against the S&P 500.")

    st.markdown("---")

    # ── Client Final State ──
    st.subheader(f"🤝 Final Client Relationship — {client.name}")
    st.markdown(f"**Status: {client.status_label()}**")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Trust",        int(client.trust))
    e2.metric("Anxiety",      int(client.anxiety))
    e3.metric("Satisfaction", int(client.satisfaction))
    e4.metric("Engagement",   int(client.engagement))

    st.markdown("---")

    # ── Qualitative Feedback ──
    st.subheader("📝 Advisor Feedback")
    if feedback["strengths"]:
        st.markdown("**✅ What you did well:**")
        for s in feedback["strengths"]:
            st.markdown(f"- {s}")
    if feedback["improvements"]:
        st.markdown("**🔧 Areas to improve:**")
        for item in feedback["improvements"]:
            st.markdown(f"- {item}")
    st.info(f"💡 **Key Insight:** {feedback['key_insight']}")

    st.markdown("---")

    # ── Session Stats ──
    with st.expander("📜 Full Session Log"):
        st.caption(f"{turns} turns completed ({turns * 6} months simulated)")
        crisis_regimes = ["Bear Market", "Market Crisis", "Rate Shock"]
        crisis_count = sum(1 for e in log if e["regime"] in crisis_regimes)
        st.caption(f"Crisis periods: {crisis_count} | Panic moves: {breakdown['panic_moves']}")
        for entry in log:
            chg = entry["emotional_changes"]
            st.markdown(
                f"**Turn {entry['turn']}** | {entry['regime']} | "
                f"Return: {fmt_pct(entry['portfolio_return'])} | "
                f"Value: ${entry['portfolio_value']:,.0f} | "
                f"Trust {'+' if chg['trust'] >= 0 else ''}{chg['trust']} | "
                f"Anxiety {'+' if chg['anxiety'] >= 0 else ''}{chg['anxiety']}"
            )

    if st.button("🔄 Start New Simulation", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.stop()


# ─────────────────────────────────────────────
# MAIN GAME SCREEN
# ─────────────────────────────────────────────

client   = st.session_state.client
market   = st.session_state.market
port_ret = st.session_state.portfolio_return
mode     = st.session_state.mode  # "learning" or "simulation"

# ── Header ───────────────────────────────────
col_title, col_status = st.columns([3, 1])
with col_title:
    mode_badge = "📘 Learning Mode" if mode == "learning" else "📈 Simulation Mode"
    st.title(f"💼 Turn {st.session_state.turn}  •  Month {st.session_state.turn * 6}")
    st.caption(mode_badge)
with col_status:
    st.markdown(f"**{client.status_label()}**")
    if mode == "simulation":
        st.caption(f"Adherence: {client.adherence_score()}%")

st.divider()

# ═══════════════════════════════════════════════════
# LEARNING MODE LAYOUT
# ═══════════════════════════════════════════════════

if mode == "learning":

    # ── Client Card (always visible, simple) ──
    st.markdown(f"### 👤 Your Client: {client.name}")
    st.markdown(f"**Goal:** {client.goal} &nbsp;|&nbsp; **Risk Tolerance:** {client.risk_tolerance.upper()}")
    st.markdown("---")

    # ── Market Summary (simple) ──
    regime_colors = {"Bull Market":"🟢","Bear Market":"🔴","Market Crisis":"🚨","Recovery":"🔵","Sideways / Flat":"🟡","Rate Shock":"🟠"}
    regime_icon = regime_colors.get(market["regime"], "⚪")
    st.markdown(f"### {regime_icon} Market This Period: {market['regime']}")
    st.caption(market["description"])

    m1, m2 = st.columns(2)
    m1.metric("Your Portfolio Return", fmt_pct(port_ret),
              help="This is how much your client's portfolio gained or lost this period")
    m2.metric("Portfolio Value", f"${st.session_state.portfolio_value:,.0f}",
              help="Total value of your client's investments")

    # Learning tip
    st.info(f"💡 **What's happening:** {st.session_state.market_commentary}")

    st.markdown("---")

    # ── Emotional State (simple bars, plain labels) ──
    st.markdown("### 🧠 How Your Client is Feeling")
    st.caption("These change based on your decisions. Keep trust high and anxiety low.")

    st.progress(int(client.trust) / 100,        text=f"Trust: {int(client.trust)}/100 — {'High ✅' if client.trust > 60 else 'Low ⚠️'}")
    st.progress(int(client.anxiety) / 100,      text=f"Anxiety: {int(client.anxiety)}/100 — {'High ⚠️' if client.anxiety > 60 else 'Normal ✅'}")
    st.progress(int(client.satisfaction) / 100, text=f"Satisfaction: {int(client.satisfaction)}/100")

    st.markdown("---")

    # ── Client Message ──
    st.markdown(f"### 💬 Message from {client.name}")
    st.warning(st.session_state.client_message)

    st.markdown("---")

    # ── Decisions (with plain explanations) ──
    st.markdown("### 🎯 Your Response")

    comm_style = st.selectbox(
        "How will you respond to them emotionally?",
        list(COMM_STYLE_EFFECTS.keys()),
        help="This affects how much your client trusts you and how anxious they feel."
    )
    # Plain English explanation of what this choice does
    effect_preview = COMM_STYLE_EFFECTS[comm_style]
    if "Dismissive" in comm_style:
        st.caption("⚠️ Warning: Dismissing client concerns almost always damages the relationship.")
    else:
        st.caption(f"→ Trust change: {'+' if effect_preview['d_trust'] >= 0 else ''}{effect_preview['d_trust']} | Anxiety change: {'+' if effect_preview['d_anxiety'] >= 0 else ''}{effect_preview['d_anxiety']}")

    recommendation = st.selectbox(
        "What will you do with their portfolio?",
        list(RECOMMENDATION_EFFECTS.keys()),
        help="This changes the actual mix of stocks, bonds, and cash."
    )
    rec_effect = RECOMMENDATION_EFFECTS[recommendation]
    if rec_effect["stock_shift"] != 0:
        new_stocks = clamp(client.portfolio["stocks"] + rec_effect["stock_shift"], 0, 1)
        st.caption(f"→ Stocks would go from {client.portfolio['stocks']*100:.0f}% to ~{new_stocks*100:.0f}%")

    # Simplified text area with guiding prompt
    free_text = st.text_area(
        "Write what you'd say to your client (optional but earns bonus points):",
        height=100,
        placeholder=f"Try: 'I understand this is stressful. Markets like this are temporary, and your portfolio is built for your goal of {client.goal}. Let's stay the course...'"
    )

    # Current allocation (collapsed by default in learning mode)
    with st.expander("📂 View current portfolio allocation", expanded=False):
        a1, a2, a3 = st.columns(3)
        a1.metric("Stocks", f"{client.portfolio['stocks']*100:.0f}%", help="Higher risk, higher potential return")
        a2.metric("Bonds",  f"{client.portfolio['bonds']*100:.0f}%",  help="Lower risk, steady income")
        a3.metric("Cash",   f"{client.portfolio['cash']*100:.0f}%",   help="Safest, but lowest return")
        lo, hi = (0.10,0.40) if client.risk_tolerance=="low" else (0.40,0.70) if client.risk_tolerance=="medium" else (0.70,0.95)
        st.caption(f"Recommended stock range for {client.risk_tolerance} risk tolerance: {int(lo*100)}%–{int(hi*100)}%")

    col_submit, col_end = st.columns([2, 1])
    with col_submit:
        submit_btn = st.button("✅ Submit & Move Forward 6 Months", type="primary", use_container_width=True)
    with col_end:
        end_btn = st.button("🏁 End & See Score", use_container_width=True)

# ═══════════════════════════════════════════════════
# SIMULATION MODE LAYOUT
# ═══════════════════════════════════════════════════

else:
    # Quick Turn toggle
    quick_turn = st.toggle("⚡ Quick Turn Mode", value=False,
                           help="Quick Turn: just dropdowns, no detailed feedback. Full Turn: everything.")

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        # Client Profile (collapsed after turn 1)
        with st.expander("👤 Client Profile", expanded=(st.session_state.turn == 1)):
            st.markdown(f"**Name:** {client.name} | **Goal:** {client.goal}")
            st.markdown(f"**Risk Tolerance:** {client.risk_tolerance.upper()}")
            st.caption(f"Loss Aversion: {client.loss_aversion} | Trust Propensity: {client.trust_propensity} | Control Preference: {client.control_preference}")

        # Market (always open)
        st.subheader("📊 Market This Period")
        regime_colors = {"Bull Market":"🟢","Bear Market":"🔴","Market Crisis":"🚨","Recovery":"🔵","Sideways / Flat":"🟡","Rate Shock":"🟠"}
        regime_icon = regime_colors.get(market["regime"], "⚪")
        st.markdown(f"### {regime_icon} {market['regime']}")
        st.caption(market["description"])

        ret_cols = st.columns(3)
        ret_cols[0].metric("Stocks", fmt_pct(market["stock_return"]))
        ret_cols[1].metric("Bonds",  fmt_pct(market["bond_return"]))
        ret_cols[2].metric("Cash",   fmt_pct(market["cash_return"]))

        st.markdown("---")
        port_cols = st.columns(2)
        port_cols[0].metric("Portfolio Return", fmt_pct(port_ret))
        port_cols[1].metric("Portfolio Value",  f"${st.session_state.portfolio_value:,.0f}")

        # Market commentary (collapsed in quick turn)
        if not quick_turn:
            st.info(f"📚 **Market Context:** {st.session_state.market_commentary}")

        # Allocation (always visible in sim mode)
        st.markdown("---")
        with st.expander("📂 Current Allocation", expanded=True):
            alloc_cols = st.columns(3)
            alloc_cols[0].metric("Stocks", f"{client.portfolio['stocks']*100:.0f}%")
            alloc_cols[1].metric("Bonds",  f"{client.portfolio['bonds']*100:.0f}%")
            alloc_cols[2].metric("Cash",   f"{client.portfolio['cash']*100:.0f}%")

    with right_col:
        # Emotional state (always open)
        st.subheader("🧠 Client Emotional State")
        em_cols = st.columns(4)
        em_cols[0].metric("Anxiety",      int(client.anxiety))
        em_cols[1].metric("Trust",        int(client.trust))
        em_cols[2].metric("Satisfaction", int(client.satisfaction))
        em_cols[3].metric("Engagement",   int(client.engagement))

        if not quick_turn:
            for label, value, _ in [("Trust", client.trust, True), ("Anxiety", client.anxiety, False), ("Satisfaction", client.satisfaction, True)]:
                st.progress(int(value) / 100, text=f"{label}: {int(value)}/100")

        st.markdown("---")

        # Client message (always open)
        st.subheader(f"💬 Message from {client.name}")
        st.warning(st.session_state.client_message)

        st.markdown("---")

        # Decisions
        st.subheader("🎯 Your Decisions")

        comm_style = st.selectbox(
            "**Communication approach**",
            list(COMM_STYLE_EFFECTS.keys()),
            help="Your communication style affects trust and anxiety more than almost anything else."
        )

        recommendation = st.selectbox(
            "**Recommendation**",
            list(RECOMMENDATION_EFFECTS.keys()),
            help="This changes the actual portfolio allocation."
        )

        rec_effect = RECOMMENDATION_EFFECTS[recommendation]
        if rec_effect["stock_shift"] != 0:
            new_stocks = clamp(client.portfolio["stocks"] + rec_effect["stock_shift"], 0, 1)
            st.caption(f"→ Stocks: {client.portfolio['stocks']*100:.0f}% → ~{new_stocks*100:.0f}%")

        # Free text only shown in full turn mode
        free_text = ""
        if not quick_turn:
            free_text = st.text_area(
                "**Your message to the client** *(optional — graded by AI)*",
                height=100,
                placeholder="e.g. 'I understand your concern. Markets like this are uncomfortable but historically temporary...'"
            )

        col_submit, col_end = st.columns([2, 1])
        with col_submit:
            submit_btn = st.button("✅ Submit & Advance 6 Months", type="primary", use_container_width=True)
        with col_end:
            end_btn = st.button("🏁 End Simulation", use_container_width=True)

# ═══════════════════════════════════════════════════
# SHARED SUBMIT LOGIC (runs for both modes)
# ═══════════════════════════════════════════════════

if end_btn:
    st.session_state.game_over = True
    st.rerun()

if submit_btn:
    st.session_state.portfolio_value *= (1 + port_ret)
    apply_recommendation(client, recommendation)

    d_trust, d_anxiety, d_sat, d_eng, breakdown = calculate_full_turn_deltas(
        client, comm_style, recommendation, market, port_ret
    )

    text_grades = None
    if free_text and len(free_text.strip()) >= 10:
        text_grades = grade_free_text_ai(
            free_text,
            st.session_state.context,
            st.session_state.context["intent"]
        )
        if text_grades:
            d_trust   += text_grades["d_trust"]
            d_anxiety += text_grades["d_anxiety"]
            d_sat     += text_grades["d_satisfaction"]
            breakdown.append(f"✍️ Written response: {text_grades['feedback']}")

    actual_changes = client.apply_emotion_deltas(d_trust, d_anxiety, d_sat, d_eng)

    st.session_state.last_feedback = {
        "breakdown":      breakdown,
        "changes":        actual_changes,
        "comm_style":     comm_style,
        "recommendation": recommendation,
        "new_allocation": dict(client.portfolio),
        "text_grades":    text_grades,
    }

    st.session_state.log.append({
        "turn":              st.session_state.turn,
        "regime":            market["regime"],
        "portfolio_return":  port_ret,
        "portfolio_value":   st.session_state.portfolio_value,
        "comm_style":        comm_style,
        "recommendation":    recommendation,
        "emotional_changes": actual_changes,
    })

    if st.session_state.turn >= 10 or client.trust < 15 or client.engagement < 10:
        st.session_state.game_over = True
        st.rerun()

    st.session_state.turn += 1
    new_market   = generate_market_turn()
    new_port_ret = calculate_portfolio_return(client.portfolio, new_market)
    new_context  = get_scenario_context(client, new_market, new_port_ret, st.session_state.turn)

    st.session_state.market            = new_market
    st.session_state.portfolio_return  = new_port_ret
    st.session_state.context           = new_context
    st.session_state.client_message    = generate_client_message_ai(new_context)
    st.session_state.market_commentary = generate_market_commentary_ai(new_market, new_port_ret, client.name)
    st.session_state.submitted         = False
    st.rerun()

# ── Feedback Panel ──
if st.session_state.last_feedback:
    fb = st.session_state.last_feedback
    with st.expander("📋 Last Turn Outcome", expanded=True):

        if mode == "simulation":
            for item in fb["breakdown"]:
                st.markdown(f"- {item}")

        st.markdown("**Emotional Changes:**")
        change_cols = st.columns(4)
        labels         = ["Trust", "Anxiety", "Satisfaction", "Engagement"]
        keys           = ["trust", "anxiety", "satisfaction", "engagement"]
        good_direction = [1, -1, 1, 1]

        for i, (label, key, good) in enumerate(zip(labels, keys, good_direction)):
            val = fb["changes"][key]
            if val == 0:
                change_cols[i].metric(label, "±0")
            elif val * good > 0:
                change_cols[i].metric(label, f"+{val}" if val > 0 else str(val), delta=str(val))
            else:
                change_cols[i].metric(label, f"+{val}" if val > 0 else str(val), delta=str(val), delta_color="inverse")

        if fb.get("text_grades"):
            tg = fb["text_grades"]
            st.markdown("**✍️ Written Response Grade:**")
            g_cols = st.columns(4)
            g_cols[0].metric("Empathy",        tg["empathy"],         help="-2 to +2")
            g_cols[1].metric("Clarity",         tg["clarity"],         help="-2 to +2")
            g_cols[2].metric("Goal Alignment",  tg["alignment"],       help="-2 to +2")
            g_cols[3].metric("Professionalism", tg["professionalism"], help="-2 to +2")
            st.caption(f"💬 {tg['feedback']}")

        new_alloc = fb["new_allocation"]
        st.caption(f"New allocation: {new_alloc['stocks']*100:.0f}% stocks / {new_alloc['bonds']*100:.0f}% bonds / {new_alloc['cash']*100:.0f}% cash")

# ── Turn History (always collapsed) ──
if st.session_state.log:
    with st.expander("📜 Turn History", expanded=False):
        for entry in reversed(st.session_state.log):
            chg = entry["emotional_changes"]
            st.markdown(
                f"**Turn {entry['turn']}** | {entry['regime']} | "
                f"Return: {fmt_pct(entry['portfolio_return'])} | "
                f"Value: ${entry['portfolio_value']:,.0f} | "
                f"Trust {'+' if chg['trust'] >= 0 else ''}{chg['trust']} | "
                f"Anxiety {'+' if chg['anxiety'] >= 0 else ''}{chg['anxiety']}"
            )
