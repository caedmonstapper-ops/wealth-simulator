"""
simulator.py — Core Game Engine
================================
This file contains ALL the logic for the simulator:
- The Client (who they are, how they feel)
- The Market (what happens each turn)
- The Rules (how decisions change outcomes)

Think of this as the "brain" of the game.
The UI (app.py) is just the "face" of the game.
Keeping them separate is good coding practice.
"""

import random


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────

def clamp(value, minimum, maximum):
    """
    Keeps a number within a range.
    Example: clamp(110, 0, 100) → 100
    Example: clamp(-5, 0, 100) → 0
    """
    return max(minimum, min(maximum, value))


def fmt_pct(decimal):
    """Converts 0.12 → '+12.00%' and -0.05 → '-5.00%'"""
    sign = "+" if decimal >= 0 else ""
    return f"{sign}{decimal * 100:.1f}%"


# ─────────────────────────────────────────────
# CLIENT CLASS
# ─────────────────────────────────────────────

class Client:
    """
    Represents a single wealth management client.

    FIXED TRAITS — set once at the start, never change:
    These are personality characteristics, like in real life.

    DYNAMIC STATE — changes every turn based on your decisions:
    These are how the client is feeling right now.
    """

    # Name pool for variety
    NAMES = ["Michael", "Sofia", "Jordan", "Ava", "Ethan", "Maya", "Carlos", "Priya"]

    # Goal pool — what the client is saving for
    GOALS = [
        "retirement at age 65",
        "buying a home in 5 years",
        "funding their children's college",
        "building generational wealth",
        "achieving financial independence",
    ]

    def __init__(self):
        # ── Fixed Personality Traits (0–100 scale) ──────────────
        # These are rolled once and stay fixed — like a real person's personality

        self.loss_aversion = random.randint(40, 90)
        # How badly losses feel. High = panics more during downturns.

        self.trust_propensity = random.randint(30, 75)
        # How quickly they trust an advisor. High = trust builds faster.

        self.control_preference = random.randint(20, 80)
        # How much they want to make their own decisions. High = harder to advise.

        self.recency_bias = random.randint(30, 85)
        # Tendency to overweight recent events. High = chases returns, panics on losses.

        # ── Risk Profile ─────────────────────────────────────────
        self.risk_tolerance = random.choice(["low", "medium", "high"])

        # ── Identity ─────────────────────────────────────────────
        self.name = random.choice(self.NAMES)
        self.goal = random.choice(self.GOALS)

        # ── Dynamic Emotional State (0–100 scale) ────────────────
        # These change every turn based on what you do

        self.anxiety = random.randint(30, 50)
        # How stressed the client is. High anxiety → poor decisions, lower trust.

        self.trust = random.randint(45, 65)
        # How much they trust you. High trust → they follow your advice.

        self.satisfaction = random.randint(45, 65)
        # Overall happiness with you as their advisor.

        self.engagement = random.randint(50, 70)
        # How involved and interested they are. Low → might leave.

        # ── Portfolio Allocation ──────────────────────────────────
        # Starting allocation (will change based on your decisions)
        self.portfolio = {
            "stocks": 0.70,
            "bonds":  0.25,
            "cash":   0.05,
        }

    def apply_emotion_deltas(self, d_trust, d_anxiety, d_satisfaction, d_engagement):
        """
        Apply emotional changes after a turn.
        Clamps everything between 0 and 100.
        Returns a dict showing what actually changed (for display).
        """
        old = {
            "trust": self.trust,
            "anxiety": self.anxiety,
            "satisfaction": self.satisfaction,
            "engagement": self.engagement,
        }

        self.trust        = clamp(self.trust        + d_trust,        0, 100)
        self.anxiety      = clamp(self.anxiety      + d_anxiety,      0, 100)
        self.satisfaction = clamp(self.satisfaction + d_satisfaction, 0, 100)
        self.engagement   = clamp(self.engagement   + d_engagement,   0, 100)

        return {
            "trust":        self.trust        - old["trust"],
            "anxiety":      self.anxiety      - old["anxiety"],
            "satisfaction": self.satisfaction - old["satisfaction"],
            "engagement":   self.engagement   - old["engagement"],
        }

    def adherence_score(self):
        """
        How likely (0–100%) is the client to actually follow your advice?
        High trust + low anxiety + low control preference = more likely to listen.
        """
        score = (
            50
            + 0.5  * self.trust
            - 0.4  * self.anxiety
            - 0.2  * (self.control_preference - 50)
        )
        return clamp(int(score), 0, 100)

    def status_label(self):
        """Returns a simple overall status based on emotional state."""
        avg = (self.trust + self.satisfaction + self.engagement) / 3
        if self.anxiety > 75:
            return "⚠️ Crisis Mode"
        if avg > 70 and self.anxiety < 40:
            return "✅ Strong Relationship"
        if avg < 40 or self.trust < 30:
            return "🔴 At Risk of Leaving"
        return "🟡 Stable"


# ─────────────────────────────────────────────
# MARKET ENGINE
# ─────────────────────────────────────────────

# Market regimes — each represents a different economic environment
# These are realistic 6-month return ranges based on historical data
MARKET_REGIMES = {
    "Bull Market": {
        "description": "Strong economic growth, rising stock prices.",
        "stocks": (0.07, 0.18),
        "bonds":  (-0.01, 0.04),
        "cash":   (0.005, 0.005),
        "client_mood_shift": -5,  # anxiety decreases in good markets
    },
    "Bear Market": {
        "description": "Broad market decline, investor pessimism.",
        "stocks": (-0.15, -0.05),
        "bonds":  (-0.02, 0.06),
        "cash":   (0.005, 0.005),
        "client_mood_shift": +12,
    },
    "Market Crisis": {
        "description": "Severe selloff. Fear and uncertainty dominate.",
        "stocks": (-0.30, -0.15),
        "bonds":  (-0.05, 0.08),
        "cash":   (0.005, 0.005),
        "client_mood_shift": +25,
    },
    "Recovery": {
        "description": "Bounce-back after a downturn. Cautious optimism.",
        "stocks": (0.08, 0.22),
        "bonds":  (-0.02, 0.05),
        "cash":   (0.005, 0.005),
        "client_mood_shift": -8,
    },
    "Sideways / Flat": {
        "description": "Low volatility, minimal movement. Boring but stable.",
        "stocks": (-0.03, 0.04),
        "bonds":  (-0.01, 0.03),
        "cash":   (0.005, 0.005),
        "client_mood_shift": 0,
    },
    "Rate Shock": {
        "description": "Rising interest rates hurt bonds and growth stocks.",
        "stocks": (-0.10, 0.02),
        "bonds":  (-0.12, -0.04),
        "cash":   (0.010, 0.020),
        "client_mood_shift": +10,
    },
}


def generate_market_turn():
    """
    Randomly selects a market regime and generates returns.
    Returns a dict with everything needed for the turn.

    KEY FIX vs old code:
    This is called ONCE per turn and stored in session state.
    The old code called this on every page render, making results random and meaningless.
    """
    regime_name = random.choice(list(MARKET_REGIMES.keys()))
    regime = MARKET_REGIMES[regime_name]

    stock_return = random.uniform(*regime["stocks"])
    bond_return  = random.uniform(*regime["bonds"])
    cash_return  = random.uniform(*regime["cash"])

    return {
        "regime":       regime_name,
        "description":  regime["description"],
        "stock_return": stock_return,
        "bond_return":  bond_return,
        "cash_return":  cash_return,
        "mood_shift":   regime["client_mood_shift"],
    }


def calculate_portfolio_return(portfolio, market):
    """
    Calculates the weighted portfolio return.
    Example: 70% stocks * +10% + 25% bonds * +2% + 5% cash * 0.5% = 7.5%
    """
    return (
        portfolio["stocks"] * market["stock_return"]
        + portfolio["bonds"]  * market["bond_return"]
        + portfolio["cash"]   * market["cash_return"]
    )


# ─────────────────────────────────────────────
# DECISION ENGINE
# ─────────────────────────────────────────────

# What stock % range is "right" for each risk tolerance
RISK_STOCK_RANGES = {
    "low":    (0.10, 0.40),
    "medium": (0.40, 0.70),
    "high":   (0.70, 0.95),
}

# Communication styles and their emotional impact
COMM_STYLE_EFFECTS = {
    "Empathize + explain calmly": {
        "d_trust": +8, "d_anxiety": -10, "d_satisfaction": +5, "d_engagement": +3,
        "label": "You acknowledged their feelings and explained your reasoning clearly."
    },
    "Data-focused reassurance": {
        "d_trust": +4, "d_anxiety": -5, "d_satisfaction": +3, "d_engagement": +2,
        "label": "You used facts and data to reassure them."
    },
    "Firm boundary (stick to the plan)": {
        "d_trust": +2, "d_anxiety": -3, "d_satisfaction": +1, "d_engagement": +1,
        "label": "You held firm on the investment plan."
    },
    "Agree and act quickly": {
        "d_trust": +3, "d_anxiety": -6, "d_satisfaction": +4, "d_engagement": +2,
        "label": "You validated their concern and moved decisively."
    },
    "Dismissive / minimize concern": {
        "d_trust": -10, "d_anxiety": +8, "d_satisfaction": -8, "d_engagement": -6,
        "label": "⚠️ You dismissed their concern. Clients rarely forgive this."
    },
}

# Recommendation choices and their portfolio + emotional impact
RECOMMENDATION_EFFECTS = {
    "Stay the course (no change)": {
        "stock_shift": 0.0,
        "bond_shift": 0.0,
        "cash_shift": 0.0,
        "d_trust": +2, "d_anxiety": 0, "d_satisfaction": +1,
        "label": "No allocation change. Staying disciplined."
    },
    "Small de-risk (−10% stocks → bonds)": {
        "stock_shift": -0.10,
        "bond_shift": +0.10,
        "cash_shift": 0.0,
        "d_trust": +3, "d_anxiety": -5, "d_satisfaction": +3,
        "label": "Modest shift toward safety. Shows responsiveness."
    },
    "Larger de-risk (−20% stocks → bonds/cash)": {
        "stock_shift": -0.20,
        "bond_shift": +0.12,
        "cash_shift": +0.08,
        "d_trust": +4, "d_anxiety": -8, "d_satisfaction": +4,
        "label": "Meaningful reduction in risk. Client will feel heard."
    },
    "Move heavily to cash (defensive)": {
        "stock_shift": -0.35,
        "bond_shift": -0.05,
        "cash_shift": +0.40,
        "d_trust": +2, "d_anxiety": -12, "d_satisfaction": +2,
        "label": "⚠️ Heavy cash move. Reduces anxiety now but sacrifices long-term growth."
    },
    "Increase risk (more stocks)": {
        "stock_shift": +0.15,
        "bond_shift": -0.10,
        "cash_shift": -0.05,
        "d_trust": -2, "d_anxiety": +5, "d_satisfaction": -2,
        "label": "⚠️ Increasing risk. Only appropriate if client is underallocated to stocks."
    },
}


def apply_recommendation(client, recommendation_key):
    """
    Adjusts the client's portfolio based on advisor's recommendation.
    Normalizes weights so they always sum to exactly 1.0 (100%).
    Returns a description of what changed.
    """
    effect = RECOMMENDATION_EFFECTS[recommendation_key]

    client.portfolio["stocks"] += effect["stock_shift"]
    client.portfolio["bonds"]  += effect["bond_shift"]
    client.portfolio["cash"]   += effect["cash_shift"]

    # Clamp each to 0–1 range first
    for k in client.portfolio:
        client.portfolio[k] = clamp(client.portfolio[k], 0.0, 1.0)

    # Normalize so they sum to 1.0
    total = sum(client.portfolio.values())
    if total > 0:
        for k in client.portfolio:
            client.portfolio[k] /= total

    return effect


def check_allocation_fit(client):
    """
    Checks if the portfolio is appropriate for the client's risk tolerance.
    Returns penalty deltas if misaligned, zeros if aligned.

    This is a KEY realism feature — even a good communication style
    can't fully compensate for a badly misaligned portfolio.
    """
    lo, hi = RISK_STOCK_RANGES[client.risk_tolerance]
    stock_pct = client.portfolio["stocks"]

    d_trust = d_anxiety = d_satisfaction = 0
    message = None

    if stock_pct < lo - 0.05:  # Too conservative (more than 5% below minimum)
        gap = lo - stock_pct
        d_satisfaction = -int(gap * 30)
        d_engagement   = -int(gap * 20)
        message = f"Portfolio is too conservative for {client.name}'s {client.risk_tolerance} risk tolerance. They may feel you're being overly cautious."
        return d_trust, d_anxiety, d_satisfaction, d_engagement, message

    elif stock_pct > hi + 0.05:  # Too aggressive (more than 5% above maximum)
        gap = stock_pct - hi
        d_anxiety   = +int(gap * 40)
        d_trust     = -int(gap * 25) if client.anxiety > 60 else 0
        d_satisfaction = -int(gap * 15)
        d_engagement = 0
        message = f"⚠️ Portfolio is too aggressive for {client.name}'s {client.risk_tolerance} risk tolerance. This is increasing their stress."
        return d_trust, d_anxiety, d_satisfaction, d_engagement, message

    d_engagement = 0
    return d_trust, d_anxiety, d_satisfaction, d_engagement, message


def calculate_full_turn_deltas(client, comm_style_key, recommendation_key, market, portfolio_return):
    """
    Master function that calculates ALL emotional changes for a turn.
    Combines:
    1. Market impact (good/bad market shifts anxiety)
    2. Communication style impact
    3. Recommendation impact
    4. Allocation fit check

    Returns final deltas and a breakdown for display.
    """
    breakdown = []

    # 1. Market-driven anxiety
    base_anxiety_shift = market["mood_shift"] * (client.loss_aversion / 100)
    d_trust        = 0
    d_anxiety      = int(base_anxiety_shift)
    d_satisfaction = 0
    d_engagement   = 0

    if d_anxiety != 0:
        direction = "increased" if d_anxiety > 0 else "decreased"
        breakdown.append(f"📈 Market conditions {direction} anxiety by {abs(d_anxiety)} pts")

    # 2. Communication style
    comm = COMM_STYLE_EFFECTS[comm_style_key]
    d_trust        += comm["d_trust"]
    d_anxiety      += comm["d_anxiety"]
    d_satisfaction += comm["d_satisfaction"]
    d_engagement   += comm["d_engagement"]
    breakdown.append(f"💬 Communication: {comm['label']}")

    # 3. Recommendation
    rec = RECOMMENDATION_EFFECTS[recommendation_key]
    d_trust        += rec["d_trust"]
    d_anxiety      += rec["d_anxiety"]
    d_satisfaction += rec["d_satisfaction"]
    breakdown.append(f"📋 Recommendation: {rec['label']}")

    # 4. Trait multipliers (personality affects how much each thing matters)
    trust_mult  = 0.75 + (client.trust_propensity / 100) * 0.5   # 0.75 to 1.25
    anxiety_mult = 0.75 + (client.loss_aversion   / 100) * 0.6   # 0.75 to 1.35

    if d_trust > 0:
        d_trust = int(d_trust * trust_mult)
    if d_anxiety > 0:
        d_anxiety = int(d_anxiety * anxiety_mult)  # anxious people feel fear more
    elif d_anxiety < 0:
        d_anxiety = int(d_anxiety / anxiety_mult)  # harder to calm a loss-averse person

    # 5. Allocation fit check
    fit_trust, fit_anxiety, fit_sat, fit_eng, fit_msg = check_allocation_fit(client)
    d_trust        += fit_trust
    d_anxiety      += fit_anxiety
    d_satisfaction += fit_sat
    d_engagement   += fit_eng
    if fit_msg:
        breakdown.append(f"⚖️ Allocation fit: {fit_msg}")

    # Final clamps
    d_trust        = clamp(d_trust,        -20, 20)
    d_anxiety      = clamp(d_anxiety,      -25, 25)
    d_satisfaction = clamp(d_satisfaction, -15, 15)
    d_engagement   = clamp(d_engagement,   -12, 12)

    return d_trust, d_anxiety, d_satisfaction, d_engagement, breakdown


# ─────────────────────────────────────────────
# CLIENT INTENT (for AI prompt context)
# ─────────────────────────────────────────────

def get_client_intent(client, portfolio_return):
    """
    Determines the emotional state/intent of the client this turn.
    Used to give the AI context for generating a realistic message.
    """
    if client.anxiety >= 80 or client.trust < 20:
        return "override_threat"       # "I want to pull everything out now"
    if client.anxiety >= 65 and portfolio_return < -0.05:
        return "panic"                 # "I'm really scared, something needs to change"
    if client.anxiety >= 55 or portfolio_return < -0.03:
        return "concerned"             # "I'm worried, can you explain this?"
    if portfolio_return > 0.08 and client.recency_bias > 65:
        return "greedy"                # "Things are great, should we go more aggressive?"
    if client.trust > 70 and client.satisfaction > 65:
        return "confident_checkin"     # "Just checking in, things seem good"
    return "neutral_checkin"           # "How are we doing?"


# ─────────────────────────────────────────────
# CAREER SCORING SYSTEM
# ─────────────────────────────────────────────

# Career titles based on final score — mirrors real wealth management career ladder
CAREER_TITLES = [
    (90, "🏆 Senior Partner",         "Elite advisor. Clients trust you completely and your portfolio management is exceptional."),
    (75, "⭐ Vice President",          "Strong advisor with excellent client relationships and solid investment discipline."),
    (60, "📈 Associate Advisor",       "Competent advisor. Good fundamentals but room to grow in crisis situations."),
    (45, "📋 Junior Advisor",          "Still developing. Focus on communication skills and risk management."),
    (0,  "📉 Probationary Advisor",    "Significant improvement needed. Review your communication and portfolio management approach."),
]

def calculate_career_score(log, client, final_portfolio_value, starting_value=100_000):
    """
    Calculates a final career score (0-100) from four weighted components.

    PROGRAMMING CONCEPT: This is a weighted scoring function.
    Each component has a maximum score and a weight (importance).
    Final score = sum of (component_score * weight)

    FINANCE CONCEPT: This mirrors how real advisory firms evaluate advisors —
    portfolio performance matters, but so does client relationship quality,
    risk management, and crisis handling.
    """
    if not log:
        return 0, {}

    # ── Component 1: Portfolio Performance (25% of score) ──────────────
    # Did the client's money grow? Compared to a simple benchmark.
    # In real finance, advisors are compared against a "benchmark" like the S&P 500.
    # Here we use a simple 5% per year (2.5% per 6-month period) as the benchmark.
    total_return = (final_portfolio_value - starting_value) / starting_value
    turns = len(log)
    benchmark_return = 0.025 * turns  # 2.5% per turn benchmark

    if total_return >= benchmark_return * 1.2:
        portfolio_score = 100
    elif total_return >= benchmark_return:
        portfolio_score = 80
    elif total_return >= 0:
        portfolio_score = 60
    elif total_return >= -0.10:
        portfolio_score = 35
    else:
        portfolio_score = 10

    # ── Component 2: Client Relationship Quality (35% of score) ─────────
    # Trust + Satisfaction + (100 - Anxiety) + Engagement, averaged
    # Anxiety is inverted because HIGH anxiety = BAD outcome
    relationship_score = (
        client.trust * 0.35
        + client.satisfaction * 0.30
        + (100 - client.anxiety) * 0.20
        + client.engagement * 0.15
    )

    # ── Component 3: Risk Management (25% of score) ──────────────────────
    # Were you consistent and disciplined, or did you panic and make big moves?
    # Count how many turns had "panic" moves or very aggressive shifts
    panic_moves = sum(
        1 for entry in log
        if "heavily to cash" in entry.get("recommendation", "").lower()
    )
    aggressive_swings = sum(
        1 for entry in log
        if "increase risk" in entry.get("recommendation", "").lower()
        and entry.get("regime") in ["Bear Market", "Market Crisis"]
    )
    bad_moves = panic_moves + aggressive_swings
    risk_score = max(0, 100 - (bad_moves * 20))

    # ── Component 4: Crisis Handling (15% of score) ───────────────────────
    # How did you perform specifically during bear markets and crises?
    # A great advisor is most valuable when markets are bad.
    crisis_turns = [
        e for e in log
        if e.get("regime") in ["Bear Market", "Market Crisis", "Rate Shock"]
    ]
    if not crisis_turns:
        crisis_score = 70  # no crises — neutral score
    else:
        # Check communication quality during crises
        good_crisis_comms = sum(
            1 for e in crisis_turns
            if any(good in e.get("comm_style", "")
                   for good in ["Empathize", "Data-focused", "Firm boundary"])
        )
        crisis_score = int((good_crisis_comms / len(crisis_turns)) * 100)

    # ── Final Weighted Score ──────────────────────────────────────────────
    final_score = int(
        portfolio_score   * 0.25
        + relationship_score * 0.35
        + risk_score         * 0.25
        + crisis_score       * 0.15
    )
    final_score = clamp(final_score, 0, 100)

    breakdown = {
        "portfolio_score":    int(portfolio_score),
        "relationship_score": int(relationship_score),
        "risk_score":         int(risk_score),
        "crisis_score":       int(crisis_score),
        "total_return_pct":   round(total_return * 100, 1),
        "benchmark_pct":      round(benchmark_return * 100, 1),
        "panic_moves":        panic_moves,
        "crisis_turns":       len(crisis_turns),
    }

    return final_score, breakdown


def get_career_title(score):
    """Returns career title and description based on score."""
    for threshold, title, description in CAREER_TITLES:
        if score >= threshold:
            return title, description
    return CAREER_TITLES[-1][1], CAREER_TITLES[-1][2]


def generate_performance_feedback(breakdown, client, log):
    """
    Generates specific, actionable feedback based on actual performance.
    This is what separates a good simulator from a great one —
    telling the user exactly what they did well and what to improve.
    """
    feedback = {"strengths": [], "improvements": [], "key_insight": ""}

    # Strengths
    if breakdown["portfolio_score"] >= 80:
        feedback["strengths"].append("Strong portfolio growth — you kept the client invested and it paid off.")
    if breakdown["relationship_score"] >= 70:
        feedback["strengths"].append("Excellent client relationship — high trust and satisfaction scores.")
    if breakdown["risk_score"] >= 80:
        feedback["strengths"].append("Disciplined risk management — you avoided panic moves.")
    if breakdown["crisis_score"] >= 75:
        feedback["strengths"].append("Strong crisis communication — you kept the client calm during downturns.")

    # Areas for improvement
    if breakdown["portfolio_score"] < 60:
        feedback["improvements"].append("Portfolio underperformed — consider staying more invested during downturns rather than moving to cash.")
    if breakdown["relationship_score"] < 55:
        feedback["improvements"].append("Client relationship needs work — prioritize empathetic communication, especially during losses.")
    if breakdown["panic_moves"] > 0:
        feedback["improvements"].append(f"You made {breakdown['panic_moves']} panic move(s) to cash — in real wealth management, this locks in losses and damages long-term returns.")
    if breakdown["crisis_score"] < 50 and breakdown["crisis_turns"] > 0:
        feedback["improvements"].append("Crisis handling needs improvement — during market downturns, empathetic explanation is more effective than data dumps or dismissiveness.")

    # Key insight (the most important lesson from this session)
    if breakdown["panic_moves"] > 1:
        feedback["key_insight"] = "The biggest wealth management lesson: staying invested through downturns is almost always better than moving to cash. Missing just the 10 best market days in a decade can cut returns in half."
    elif breakdown["relationship_score"] < 50:
        feedback["key_insight"] = "The biggest wealth management lesson: clients don't leave advisors because of bad markets — they leave because of bad communication during bad markets."
    elif breakdown["portfolio_score"] >= 80 and breakdown["relationship_score"] >= 70:
        feedback["key_insight"] = "You demonstrated the core skill of wealth management: balancing investment discipline with behavioral coaching. That combination is what separates great advisors."
    else:
        feedback["key_insight"] = "Wealth management is 20% investment knowledge and 80% behavioral psychology. The best advisors are the ones who can keep clients calm and invested through volatility."

    return feedback


def get_scenario_context(client, market, portfolio_return, turn_number):
    """
    Builds a rich context string to send to Claude AI for generating the client message.
    The more context the AI has, the more realistic and personalized the message.
    """
    intent = get_client_intent(client, portfolio_return)

    intent_descriptions = {
        "override_threat":   "extremely anxious and threatening to override you and move everything to cash",
        "panic":             "panicking and demanding action, not thinking clearly",
        "concerned":         "genuinely worried and asking for explanation and reassurance",
        "greedy":            "excited by recent gains and pushing to take on more risk",
        "confident_checkin": "happy and satisfied, doing a routine check-in",
        "neutral_checkin":   "calm and checking in on progress toward their goal",
    }

    return {
        "intent": intent,
        "intent_description": intent_descriptions[intent],
        "client_name": client.name,
        "client_goal": client.goal,
        "risk_tolerance": client.risk_tolerance,
        "loss_aversion": client.loss_aversion,
        "anxiety": int(client.anxiety),
        "trust": int(client.trust),
        "satisfaction": int(client.satisfaction),
        "portfolio_return_pct": f"{portfolio_return * 100:.1f}%",
        "portfolio_value_direction": "gained" if portfolio_return >= 0 else "lost",
        "regime": market["regime"],
        "regime_description": market["description"],
        "turn_number": turn_number,
        "stocks_pct": int(client.portfolio["stocks"] * 100),
        "bonds_pct": int(client.portfolio["bonds"] * 100),
        "cash_pct": int(client.portfolio["cash"] * 100),
    }
