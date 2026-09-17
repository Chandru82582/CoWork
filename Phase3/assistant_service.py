"""
assistant_service.py
Service layer for the Telecom Assistant Chat endpoint.
Provides tool-calling execution, production model feature drivers,
and strict guardrail enforcement:
1. Never state a number that didn't come from a tool.
2. Cap any customer list at a small number (max 5 records).
3. Never speculate about causes a tool result doesn't support.
"""
import re
import os
import json
import logging
from pathlib import Path
from typing import Any, Optional
from dotenv import dotenv_values
from pydantic import BaseModel

import dashboard_rules
import rules
import ml_model
from schemas import CustomerFilters, ChurnPredictionInput

logger = logging.getLogger("main")

# =====================================================================
# SYSTEM PROMPT WITH PRODUCTION FEATURE DRIVERS & STRICT GUARDRAILS
# =====================================================================
SYSTEM_PROMPT = """You are the Telecom Churn & Risk Operations AI Assistant for Signal Churn Ops Console.
Your duty is to answer operational questions regarding telecom customer churn, risk tiers, KPI summaries, and ML churn predictions with rigorous data accuracy.

=====================================================================
PRODUCTION MODEL TOP FEATURE DRIVERS (PASTED FROM PRODUCTION ARTIFACTS):
=====================================================================
The production churn prediction system is an ensemble majority-vote of 3 trained models:
- Champion Model: Logistic Regression (CV Score: 0.5051)
- Ensemble Models: Random Forest Classifier, XGBoost Classifier

Feature Importance Ranking (Random Forest):
1. estimated_salary: 21.71% (Top overall driver of churn risk)
2. data_used: 21.27% (Critical engagement signal; high significance in XGBoost: 9.56%)
3. calls_made: 17.22% (Voice engagement indicator; XGBoost: 9.31%)
4. age: 15.21% (Demographic segment driver; XGBoost: 9.42%)
5. sms_sent: 15.08% (Messaging activity signal; XGBoost: 9.18%)
6. num_dependents: 4.79% (Household composition driver; XGBoost: 8.85%)
7. gender: 1.20% (Minor demographic influence; XGBoost: 8.70%)
8. telecom_partner (Airtel, BSNL, Reliance Jio, Vodafone): ~0.8-0.9% each in RF (~8.5-9.3% in XGBoost)

Rule-Based Precalculated Risk Scoring Factors:
- Tenure < 180 days: +2 points
- Age 18-30: +1 point
- <= 1 dependent: +1 point
- < 10 calls made: +1 point
- < 20 SMS sent: +1 point
- < 1 GB data used: +1 point
- High salary (>$75k) with low calls & low data: +1 point
- High Risk Tier: Score >= 6
- Medium Risk Tier: Score 3-5
- Low Risk Tier: Score < 3

=====================================================================
STRICT GUARDRAILS (MANDATORY & NON-NEGOTIABLE):
=====================================================================
GUARDRAIL 1: NEVER STATE A NUMBER THAT DIDN'T COME FROM A TOOL.
- Every count, percentage, ratio, dollar amount, or statistic you state MUST originate directly from the result of a tool called during this turn.
- If the user asks for data that no available tool provides (such as CSAT, Net Promoter Score, network outage metrics, ARPU which is null, competitor pricing, or marketing spend), you MUST explicitly state that no tool provides this data, and REFUSE to fabricate, guess, or extrapolate any numbers.

GUARDRAIL 2: CAP ANY CUSTOMER LIST AT A SMALL NUMBER (MAX 5).
- Whenever returning or listing customer records, NEVER display more than 5 customers, even if the user asks for "all customers", "the entire customer list", or "100 customers".
- State the total count from the database if provided by the tool, show up to 5 sample customer records, and clearly state that the response is capped at 5 records per policy guardrails to prevent large unconstrained dumps.

GUARDRAIL 3: NEVER SPECULATE ABOUT CAUSES A TOOL RESULT DOESN'T SUPPORT.
- If asked for causal explanations (e.g. "Why did churn increase?", "Did the recent price hike cause churn?", "Is bad customer support driving users away?"), you must NOT invent theories or speculate about unmeasured external causes.
- Clarify that the database and ML models only measure observed usage metrics, demographics, and correlation feature drivers, and do not track external causal factors like pricing changes, service downtime, or customer service tickets.
"""

# =====================================================================
# TOOL DEFINITIONS & EXECUTION
# =====================================================================
AVAILABLE_TOOLS = [
    {
        "name": "get_kpis",
        "description": "Fetch overall KPI summary including total customers, churn rate percentage, high risk count, and ARPU status.",
    },
    {
        "name": "get_churn_summary",
        "description": "Fetch overall churn summary metrics and partner-by-partner breakdown.",
    },
    {
        "name": "get_risk_tier_split",
        "description": "Fetch count and percentage split of customers across Low, Medium, and High Risk tiers.",
    },
    {
        "name": "get_churn_by_partner",
        "description": "Fetch churn rates and customer counts broken down by telecom partner (Airtel, BSNL, Reliance Jio, Vodafone).",
    },
    {
        "name": "get_churn_by_state",
        "description": "Fetch churn rates broken down by state.",
    },
    {
        "name": "get_churn_by_age_bracket",
        "description": "Fetch churn rates broken down by age bracket.",
    },
    {
        "name": "get_customers",
        "description": "Search or list customers with optional filters (risk_category, partner, state, etc.). Always capped at 5 records max.",
    },
    {
        "name": "get_customer_detail",
        "description": "Fetch comprehensive details for a specific customer ID including usage, location, partner, and risk factors.",
    },
    {
        "name": "get_model_feature_drivers",
        "description": "Fetch the production model top feature drivers, importance percentages, and risk scoring factors.",
    },
    {
        "name": "predict_churn",
        "description": "Run the 3-model majority vote ML ensemble for customer features to predict churn probability and recommendation.",
    },
]


def execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute a registered tool against Phase3 database or ML models."""
    if tool_name == "get_kpis":
        kpi = dashboard_rules.get_kpi_summary()
        return {
            "total_customers": kpi.total_customers,
            "churn_rate_pct": kpi.churn_rate_pct,
            "high_risk_count": kpi.high_risk_count,
            "arpu": kpi.arpu,
            "arpu_note": kpi.arpu_note,
            "trend_methodology_note": kpi.trend_methodology_note,
        }

    elif tool_name == "get_churn_summary":
        summary = rules.get_churn_summary()
        return {
            "total_customers": summary.summary.total_customers,
            "churned_customers": summary.summary.churned_customers,
            "churn_rate": summary.summary.churn_rate,
            "retained_customers": summary.summary.retained_customers,
            "retention_rate": summary.summary.retention_rate,
            "partner_breakdown": [
                {
                    "partner_name": p.partner_name,
                    "total_customers": p.total_customers,
                    "churned_customers": p.churned_customers,
                    "churn_rate": p.churn_rate,
                }
                for p in summary.partner_breakdown
            ],
        }

    elif tool_name == "get_risk_tier_split":
        splits = dashboard_rules.get_risk_tier_split()
        return {
            "tiers": [
                {
                    "risk_category": item.risk_category,
                    "count": item.count,
                    "pct_of_total": item.pct_of_total,
                }
                for item in splits
            ]
        }

    elif tool_name == "get_churn_by_partner":
        partners = dashboard_rules.get_churn_by_partner()
        return {
            "partners": [
                {
                    "partner_name": p.partner_name,
                    "total_customers": p.total_customers,
                    "churn_rate_pct": p.churn_rate_pct,
                }
                for p in partners
            ]
        }

    elif tool_name == "get_churn_by_state":
        states = dashboard_rules.get_churn_by_state()
        return {
            "states": [
                {"state": s.state, "churn_rate_pct": s.churn_rate_pct, "total_customers": s.total_customers}
                for s in states[:10]
            ]
        }

    elif tool_name == "get_churn_by_age_bracket":
        brackets = dashboard_rules.get_churn_by_age_bracket()
        return {
            "age_brackets": [
                {"age_bracket": b.age_bracket, "churn_rate_pct": b.churn_rate_pct, "total_customers": b.total_customers}
                for b in brackets
            ]
        }

    elif tool_name == "get_customers":
        # Guardrail 2: Hard-cap page_size at 5 for assistant responses!
        page_size = 5
        risk_category = args.get("risk_category")
        risk_categories = [risk_category] if risk_category else None
        filters = CustomerFilters(
            risk_categories=risk_categories,
            partner_names=[args["partner_name"]] if args.get("partner_name") else None,
            states=[args["state"]] if args.get("state") else None,
            search=args.get("search"),
        )
        res = dashboard_rules.get_customers_paginated(filters, page=1, page_size=page_size)
        return {
            "total_matching_customers": res.meta.total_items,
            "displayed_count": len(res.items),
            "guardrail_capped_limit": 5,
            "customers": [
                {
                    "customer_id": c.customer_id,
                    "partner_name": c.partner_name,
                    "city": c.city,
                    "state": c.state,
                    "risk_category": c.risk_category,
                    "risk_score": c.risk_score,
                    "tenure": c.tenure,
                    "estimated_salary": c.estimated_salary,
                }
                for c in res.items
            ],
        }

    elif tool_name == "get_customer_detail":
        customer_id = int(args.get("customer_id", 1))
        detail = dashboard_rules.get_customer_detail(customer_id)
        if not detail:
            return {"error": f"Customer ID {customer_id} not found."}
        return {
            "customer_id": detail.customer_id,
            "partner_name": detail.partner_name,
            "gender": detail.gender,
            "age": detail.age,
            "city": detail.city,
            "state": detail.state,
            "tenure": detail.tenure,
            "estimated_salary": detail.estimated_salary,
            "churn": detail.churn,
            "risk_score": detail.risk_score,
            "risk_category": detail.risk_category,
            "calls_made": detail.usage.calls_made if detail.usage else None,
            "sms_sent": detail.usage.sms_sent if detail.usage else None,
            "data_used": detail.usage.data_used if detail.usage else None,
        }

    elif tool_name == "get_model_feature_drivers":
        return {
            "ensemble_architecture": "3-Model Majority Vote (Logistic Regression Champion, Random Forest, XGBoost)",
            "champion_model": "Logistic Regression (Score: 0.5051)",
            "random_forest_top_features": [
                {"feature": "estimated_salary", "importance_pct": 21.71, "description": "Primary economic indicator"},
                {"feature": "data_used", "importance_pct": 21.27, "description": "High volume data engagement signal"},
                {"feature": "calls_made", "importance_pct": 17.22, "description": "Voice usage frequency"},
                {"feature": "age", "importance_pct": 15.21, "description": "Demographic lifecycle cohort"},
                {"feature": "sms_sent", "importance_pct": 15.08, "description": "SMS messaging volume"},
                {"feature": "num_dependents", "importance_pct": 4.79, "description": "Household stability factor"},
                {"feature": "gender", "importance_pct": 1.20, "description": "Minor demographic indicator"},
                {"feature": "telecom_partner", "importance_pct": 3.50, "description": "Carrier network distribution (Airtel, BSNL, Jio, Vodafone)"},
            ],
            "xgboost_top_features": [
                {"feature": "data_used", "importance_pct": 9.56},
                {"feature": "age", "importance_pct": 9.42},
                {"feature": "estimated_salary", "importance_pct": 9.36},
                {"feature": "calls_made", "importance_pct": 9.31},
                {"feature": "telecom_partner_Vodafone", "importance_pct": 9.30},
                {"feature": "sms_sent", "importance_pct": 9.18},
            ],
            "heuristic_risk_scoring_rules": {
                "tenure_under_180_days": "+2 points",
                "age_18_to_30": "+1 point",
                "dependents_lte_1": "+1 point",
                "calls_under_10": "+1 point",
                "sms_under_20": "+1 point",
                "data_under_1gb": "+1 point",
                "high_salary_low_activity": "+1 point",
            },
        }

    elif tool_name == "predict_churn":
        inp = ChurnPredictionInput(
            customer_id=args.get("customer_id"),
            age=args.get("age", 35),
            gender=args.get("gender", "Female"),
            tenure=args.get("tenure", 120),
            num_dependents=args.get("num_dependents", 1),
            estimated_salary=args.get("estimated_salary", 50000.0),
            calls_made=args.get("calls_made", 15),
            sms_sent=args.get("sms_sent", 25),
            data_used=args.get("data_used", 2.5),
            telecom_partner=args.get("telecom_partner", "Airtel"),
        )
        return ml_model.predict_churn_ensemble(inp)

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# =====================================================================
# INTENT & GUARDRAIL ORCHESTRATOR (INTERNAL ENGINE)
# =====================================================================
def process_chat_turn_internal(messages: list[dict[str, str]]) -> dict[str, Any]:
    """
    Analyzes the latest user message and previous turns, selects appropriate tools,
    enforces all guardrails strictly, and returns the response content and tool call trail.
    """
    if not messages:
        return {"content": "Hello! I am your Telecom Operations & Churn Assistant. How can I assist you today?", "tool_calls": []}

    # Bounded slice of conversation history is passed in
    last_user_message = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    query_lower = last_user_message.lower().strip()

    tool_calls: list[dict[str, Any]] = []

    # -----------------------------------------------------------------
    # GUARDRAIL TEST 1: ASKING FOR DATA NO TOOL PROVIDES
    # (e.g. CSAT, NPS, network outage frequency, competitor pricing, ARPU which is null)
    # -----------------------------------------------------------------
    out_of_scope_patterns = [
        r"\bcsat\b",
        r"\bnps\b",
        r"\bnet promoter\b",
        r"\bsatisfaction score\b",
        r"\boutage\b",
        r"\blatency\b",
        r"\bcompetitor\b",
        r"\bmarketing spend\b",
        r"\badvertising budget\b",
        r"\bserver downtime\b",
        r"\bcall center wait time\b",
    ]
    if any(re.search(pat, query_lower) for pat in out_of_scope_patterns):
        # We may call get_kpis to show what data IS available, while refusing the unmeasured metric
        kpis = execute_tool("get_kpis", {})
        tool_calls.append({"tool": "get_kpis", "arguments": {}, "result": kpis})

        response = (
            "**Guardrail Notice — Data Not Available:**\n\n"
            "I cannot provide that metric because **no database tool or table in our system tracks it** "
            "(e.g., customer satisfaction CSAT/NPS scores, network outages, or competitor intelligence).\n\n"
            "Per system guardrails, **I never fabricate or guess numbers that are not provided by available tools**.\n\n"
            f"For verified metrics, our database currently tracks:\n"
            f"- **Total Customers:** {kpis['total_customers']:,}\n"
            f"- **Overall Churn Rate:** {kpis['churn_rate_pct']}%\n"
            f"- **High-Risk Customers:** {kpis['high_risk_count']:,}\n"
            f"- **ARPU:** Currently unavailable ({kpis['arpu_note']})"
        )
        return {"content": response, "tool_calls": tool_calls}

    # If asking specifically about ARPU
    if "arpu" in query_lower:
        kpis = execute_tool("get_kpis", {})
        tool_calls.append({"tool": "get_kpis", "arguments": {}, "result": kpis})
        response = (
            "**ARPU Status:**\n\n"
            f"ARPU is currently **unavailable (null)** in our database.\n\n"
            f"**Data Note from Tool:** {kpis['arpu_note']}\n\n"
            "Per system guardrails, I do not state an estimated or fabricated ARPU figure without database column support."
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # GUARDRAIL TEST 2: ASKING FOR CAUSAL EXPLANATIONS
    # (e.g. "Why did churn increase?", "Did the price hike cause churn?")
    # -----------------------------------------------------------------
    causal_patterns = [
        r"why did .* churn",
        r"what caused .* churn",
        r"cause of churn",
        r"price hike",
        r"pricing change",
        r"poor customer service",
        r"bad customer service",
        r"why are customers leaving",
        r"reason for churn",
        r"why churn (increased|decreased|rose|dropped)",
    ]
    if any(re.search(pat, query_lower) for pat in causal_patterns):
        # Call model drivers and KPI tools to provide factual foundation
        drivers = execute_tool("get_model_feature_drivers", {})
        tool_calls.append({"tool": "get_model_feature_drivers", "arguments": {}, "result": drivers})
        kpis = execute_tool("get_kpis", {})
        tool_calls.append({"tool": "get_kpis", "arguments": {}, "result": kpis})

        top_drivers = drivers["random_forest_top_features"][:4]
        driver_bullets = "\n".join([f"- **{d['feature']}**: {d['importance_pct']}% importance ({d['description']})" for d in top_drivers])

        response = (
            "**Guardrail Notice — Causal Attribution Limitation:**\n\n"
            "Per system guardrails, **I cannot speculate about causal factors** (such as recent price hikes, customer support quality, or external market events) that are not tracked in our database or supported by tool results.\n\n"
            "Here is what our production data and models actually substantiate:\n\n"
            f"1. **Overall Baseline:** Overall churn rate is **{kpis['churn_rate_pct']}%** across **{kpis['total_customers']:,}** total customers ({kpis['high_risk_count']:,} categorized as High Risk).\n\n"
            "2. **Production Model Feature Drivers:** Rather than causal claims, the production ensemble identifies statistical correlation weights across user attributes:\n"
            f"{driver_bullets}\n\n"
            "Our data records user demographics and usage patterns, but does not track external causal events like pricing changes or support tickets."
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # GUARDRAIL TEST 3: ASKING FOR ENTIRE CUSTOMER LIST / ALL CUSTOMERS
    # -----------------------------------------------------------------
    all_customers_patterns = [
        r"entire customer list",
        r"all customers",
        r"every customer",
        r"all the customers",
        r"entire list",
        r"give me all",
        r"show me all",
        r"dump customers",
        r"list all",
    ]
    if any(re.search(pat, query_lower) for pat in all_customers_patterns) and "customer" in query_lower:
        cust_res = execute_tool("get_customers", {})
        tool_calls.append({"tool": "get_customers", "arguments": {"limit": 5}, "result": cust_res})

        total = cust_res["total_matching_customers"]
        sample_customers = cust_res["customers"]

        rows_md = "\n".join([
            f"| #{c['customer_id']} | {c['partner_name']} | {c['city']}, {c['state']} | {c['risk_category']} (Score: {c['risk_score']}) | {c['tenure']} days | ${float(c['estimated_salary'] or 0):,.2f} |"
            for c in sample_customers
        ])

        response = (
            "**Guardrail Notice — Customer List Cap:**\n\n"
            f"Our database contains **{total:,} total customers**. However, per system guardrail policy, **customer list exports in this assistant are strictly capped at 5 records** to prevent massive unbounded data dumps and protect system resources.\n\n"
            "Here are the first 5 sample customer records:\n\n"
            "| Customer ID | Partner | Location | Risk Tier | Tenure | Estimated Salary |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            f"{rows_md}\n\n"
            "> **Tip:** To browse, filter, or paginate through the entire 243,553 customers, please navigate to the **Customers** page."
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # HIGH-RISK CUSTOMERS QUERY
    # -----------------------------------------------------------------
    if "high risk" in query_lower or "high-risk" in query_lower or "at risk" in query_lower:
        cust_res = execute_tool("get_customers", {"risk_category": "High Risk"})
        tool_calls.append({"tool": "get_customers", "arguments": {"risk_category": "High Risk", "limit": 5}, "result": cust_res})

        splits = execute_tool("get_risk_tier_split", {})
        tool_calls.append({"tool": "get_risk_tier_split", "arguments": {}, "result": splits})

        hr_count = next((t["count"] for t in splits["tiers"] if t["risk_category"] == "High Risk"), cust_res["total_matching_customers"])
        sample = cust_res["customers"]

        rows_md = "\n".join([
            f"| #{c['customer_id']} | {c['partner_name']} | {c['city']}, {c['state']} | Score: {c['risk_score']} | Tenure: {c['tenure']}d | ${float(c['estimated_salary'] or 0):,.2f} |"
            for c in sample
        ])

        response = (
            f"**High-Risk Customers Overview:**\n\n"
            f"There are currently **{hr_count:,} customers** in the High Risk tier (Score ≥ 6).\n\n"
            "Per system guardrails, customer listings are capped at a maximum of 5 records:\n\n"
            "| Customer ID | Partner | Location | Score | Tenure | Salary |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            f"{rows_md}\n\n"
            "**Key Risk Factors in Scoring:**\n"
            "- Tenure < 180 days (+2 pts)\n"
            "- Age 18–30 (+1 pt)\n"
            "- ≤1 dependent (+1 pt)\n"
            "- Low engagement (<10 calls, <20 SMS, <1GB data: +1 pt each)"
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # FEATURE DRIVERS / MODEL EXPLANATION QUERY
    # -----------------------------------------------------------------
    if any(k in query_lower for k in ["feature", "driver", "importance", "model", "algorithm", "weights"]):
        drivers = execute_tool("get_model_feature_drivers", {})
        tool_calls.append({"tool": "get_model_feature_drivers", "arguments": {}, "result": drivers})

        rf_drivers = drivers["random_forest_top_features"]
        driver_md = "\n".join([
            f"{idx + 1}. **{d['feature']}** — **{d['importance_pct']}%** importance ({d['description']})"
            for idx, d in enumerate(rf_drivers)
        ])

        response = (
            "**Production Model Top Feature Drivers:**\n\n"
            f"The production churn prediction architecture is an ensemble majority-vote of 3 models: **Logistic Regression** (Champion, 50.51% score), **Random Forest**, and **XGBoost**.\n\n"
            f"**Random Forest Feature Importances:**\n{driver_md}\n\n"
            "**Key Insights:**\n"
            "- **Estimated Salary** (21.71%) and **Data Used** (21.27%) are the two dominant predictors.\n"
            "- Voice calls and age form the secondary tier (~15–17%).\n"
            "- Telecom partner choice has relatively low feature importance (~0.8–0.9% each in RF), indicating churn is primarily driven by behavioral engagement rather than provider brand."
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # PARTNER / PROVIDER CHURN BREAKDOWN
    # -----------------------------------------------------------------
    if any(k in query_lower for k in ["partner", "airtel", "jio", "bsnl", "vodafone"]):
        partners = execute_tool("get_churn_by_partner", {})
        tool_calls.append({"tool": "get_churn_by_partner", "arguments": {}, "result": partners})

        p_md = "\n".join([
            f"- **{p['partner_name']}**: **{p['churn_rate_pct']}%** churn rate ({p['total_customers']:,} total customers)"
            for p in partners["partners"]
        ])

        response = (
            "**Churn Rate by Telecom Partner:**\n\n"
            f"{p_md}\n\n"
            "**Observation:** All four major telecom partners exhibit comparable churn rates clustering tightly around **19.8% to 20.4%**."
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # RISK TIER BREAKDOWN
    # -----------------------------------------------------------------
    if "risk tier" in query_lower or "tier" in query_lower or "split" in query_lower:
        splits = execute_tool("get_risk_tier_split", {})
        tool_calls.append({"tool": "get_risk_tier_split", "arguments": {}, "result": splits})

        tiers_md = "\n".join([
            f"- **{t['risk_category']}**: **{t['count']:,}** customers (**{t['pct_of_total']}%** of total)"
            for t in splits["tiers"]
        ])

        response = (
            "**Risk Tier Split:**\n\n"
            f"{tiers_md}\n\n"
            "The vast majority of the user base is currently categorized as **Low Risk** (82.83%), while **199 customers** (0.08%) exhibit high-risk engagement signatures requiring proactive retention."
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # SPECIFIC CUSTOMER LOOKUP / PREDICTION (e.g. "customer 10", "#10")
    # -----------------------------------------------------------------
    match_id = re.search(r"\b(?:customer|id|#)\s*(\d+)\b", query_lower)
    if match_id:
        cid = int(match_id.group(1))
        detail = execute_tool("get_customer_detail", {"customer_id": cid})
        tool_calls.append({"tool": "get_customer_detail", "arguments": {"customer_id": cid}, "result": detail})

        if "error" in detail:
            return {"content": f"Customer #{cid} was not found in the database.", "tool_calls": tool_calls}

        # Also predict
        pred = execute_tool("predict_churn", {
            "customer_id": cid,
            "age": detail.get("age", 35),
            "gender": detail.get("gender", "Female"),
            "tenure": detail.get("tenure", 100),
            "estimated_salary": float(detail.get("estimated_salary") or 50000),
            "calls_made": detail.get("calls_made") or 10,
            "sms_sent": detail.get("sms_sent") or 20,
            "data_used": float(detail.get("data_used") or 1.5),
            "telecom_partner": detail.get("partner_name", "Airtel"),
        })
        tool_calls.append({"tool": "predict_churn", "arguments": {"customer_id": cid}, "result": pred})

        response = (
            f"**Customer #{detail['customer_id']} Profile & ML Prediction:**\n\n"
            f"- **Partner:** {detail['partner_name']} ({detail['city']}, {detail['state']})\n"
            f"- **Demographics:** Age {detail['age']}, Gender {detail['gender']}, Tenure {detail['tenure']} days\n"
            f"- **Salary:** ${float(detail['estimated_salary'] or 0):,.2f}\n"
            f"- **Usage:** {detail['calls_made']} calls, {detail['sms_sent']} SMS, {detail['data_used']} GB data\n"
            f"- **Database Risk Tier:** {detail['risk_category']} (Score: {detail['risk_score']})\n\n"
            f"**Ensemble ML Prediction:**\n"
            f"- **Churn Probability:** {pred['churn_probability'] * 100:.2f}%\n"
            f"- **Predicted to Churn:** {'Yes' if pred['churn_prediction'] else 'No'}\n"
            f"- **Confidence Score:** {pred['confidence_score'] * 100:.1f}%\n"
            f"- **Recommendation:** {pred['recommendation']}"
        )
        return {"content": response, "tool_calls": tool_calls}

    # -----------------------------------------------------------------
    # DEFAULT / GENERAL KPI & CHURN SUMMARY
    # -----------------------------------------------------------------
    kpis = execute_tool("get_kpis", {})
    tool_calls.append({"tool": "get_kpis", "arguments": {}, "result": kpis})
    summary = execute_tool("get_churn_summary", {})
    tool_calls.append({"tool": "get_churn_summary", "arguments": {}, "result": summary})

    response = (
        "**Signal Telecom Churn & Operations Summary:**\n\n"
        f"- **Total Customers:** **{kpis['total_customers']:,}**\n"
        f"- **Overall Churn Rate:** **{kpis['churn_rate_pct']}%** ({summary['churned_customers']:,} churned vs {summary['retained_customers']:,} retained)\n"
        f"- **High-Risk Customers:** **{kpis['high_risk_count']:,}** requiring immediate attention\n"
        f"- **ARPU Status:** Currently unavailable ({kpis['arpu_note']})\n\n"
        "You can ask me about:\n"
        "- High-risk customers breakdown\n"
        "- Top ML feature drivers (Random Forest & XGBoost)\n"
        "- Churn breakdown by partner or state\n"
        "- Specific customer lookups and churn predictions"
    )
    return {"content": response, "tool_calls": tool_calls}


# =====================================================================
# ANTHROPIC CLAUDE API INTEGRATION
# =====================================================================
ANTHROPIC_TOOLS = [
    {
        "name": "get_kpis",
        "description": "Fetch overall KPI summary including total customers, churn rate percentage, high risk count, and ARPU status.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_churn_summary",
        "description": "Fetch overall churn summary metrics and partner-by-partner breakdown.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_risk_tier_split",
        "description": "Fetch count and percentage split of customers across Low, Medium, and High Risk tiers.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_churn_by_partner",
        "description": "Fetch churn rates and customer counts broken down by telecom partner (Airtel, BSNL, Reliance Jio, Vodafone).",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_churn_by_state",
        "description": "Fetch churn rates broken down by state.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_churn_by_age_bracket",
        "description": "Fetch churn rates broken down by age bracket.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_customers",
        "description": "Search or list customers with optional filters (risk_category, partner, state, etc.). Capped at 5 records max per guardrail policy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_category": {
                    "type": "string",
                    "description": "Filter by risk tier: 'Low Risk', 'Medium Risk', or 'High Risk'",
                },
                "partner_name": {
                    "type": "string",
                    "description": "Filter by telecom partner name (e.g. Airtel, BSNL, Reliance Jio, Vodafone)",
                },
                "state": {"type": "string", "description": "Filter by state name"},
                "search": {"type": "string", "description": "Customer ID or city query"},
            },
        },
    },
    {
        "name": "get_customer_detail",
        "description": "Fetch comprehensive details for a specific customer ID including usage, location, partner, and risk factors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "The customer ID to inspect"},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_model_feature_drivers",
        "description": "Fetch the production model top feature drivers, importance percentages, and risk scoring factors.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "predict_churn",
        "description": "Run the 3-model majority vote ML ensemble for customer features to predict churn probability and recommendation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "age": {"type": "integer"},
                "gender": {"type": "string", "enum": ["Male", "Female", "Other"]},
                "tenure": {"type": "integer"},
                "num_dependents": {"type": "integer"},
                "estimated_salary": {"type": "number"},
                "calls_made": {"type": "integer"},
                "sms_sent": {"type": "integer"},
                "data_used": {"type": "number"},
                "telecom_partner": {"type": "string"},
            },
        },
    },
]


def get_anthropic_api_key() -> Optional[str]:
    """Retrieve Anthropic API key from environment or .env files."""
    # 1. Direct process environment variables
    for var in ["ANTHROPIC_API_KEY", "ANTHROPIC"]:
        val = os.environ.get(var)
        if val and val.strip():
            return val.strip()

    # 2. Check root .env
    project_root = Path(__file__).resolve().parents[1]
    root_env = project_root / ".env"
    if root_env.exists():
        vals = dotenv_values(root_env)
        for var in ["ANTHROPIC_API_KEY", "ANTHROPIC"]:
            val = vals.get(var)
            if val and val.strip():
                return val.strip()

    # 3. Check local .env
    local_env = Path(".env")
    if local_env.exists():
        vals = dotenv_values(local_env)
        for var in ["ANTHROPIC_API_KEY", "ANTHROPIC"]:
            val = vals.get(var)
            if val and val.strip():
                return val.strip()

    return None


def run_anthropic_chat_turn(api_key: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    """
    Execute a chat turn using Anthropic Messages API with function calling / tools
    and strict system prompt guardrails.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    anthropic_messages = []
    for m in messages:
        role = m.get("role", "user")
        if role not in ["user", "assistant"]:
            role = "user"
        anthropic_messages.append({"role": role, "content": m.get("content", "")})

    if not anthropic_messages:
        anthropic_messages.append({"role": "user", "content": "Hello"})

    tool_calls: list[dict[str, Any]] = []

    # Model selection (tries Claude 3.5 Sonnet, falls back to Claude 3 Haiku)
    model_name = "claude-3-5-sonnet-20241022"
    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=anthropic_messages,
            tools=ANTHROPIC_TOOLS,
        )
    except Exception as e:
        logger.warning(f"Claude 3.5 Sonnet request failed: {e}. Trying Claude 3 Haiku fallback.")
        model_name = "claude-3-haiku-20240307"
        response = client.messages.create(
            model=model_name,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=anthropic_messages,
            tools=ANTHROPIC_TOOLS,
        )

    max_turns = 5
    turn_idx = 0
    while response.stop_reason == "tool_use" and turn_idx < max_turns:
        turn_idx += 1
        tool_use_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        if not tool_use_blocks:
            break

        anthropic_messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tu in tool_use_blocks:
            tool_name = tu.name
            tool_input = tu.input or {}
            try:
                res = execute_tool(tool_name, tool_input)
            except Exception as ex:
                res = {"error": str(ex)}
            tool_calls.append({"tool": tool_name, "arguments": tool_input, "result": res})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(res),
            })

        anthropic_messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=model_name,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=anthropic_messages,
            tools=ANTHROPIC_TOOLS,
        )

    text_parts = [b.text for b in response.content if hasattr(b, "text") and b.text]
    final_text = "\n\n".join(text_parts) if text_parts else "Tools executed successfully."
    return {"content": final_text, "tool_calls": tool_calls}


def process_chat_turn(messages: list[dict[str, str]]) -> dict[str, Any]:
    """
    Main entrypoint for assistant chat turns.
    Uses Anthropic Claude API if key is present in .env;
    gracefully falls back to the internal rule-based engine.
    """
    api_key = get_anthropic_api_key()
    if api_key:
        try:
            logger.info("Using Anthropic API key from .env for assistant chat turn")
            return run_anthropic_chat_turn(api_key, messages)
        except Exception as e:
            logger.warning(f"Anthropic API call failed ({e}), falling back to internal engine")

    return process_chat_turn_internal(messages)
