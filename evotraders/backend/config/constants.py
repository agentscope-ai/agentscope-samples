# -*- coding: utf-8 -*-
# flake8: noqa: E501
# pylint: disable=C0301

# Agent configuration for dashboard display
AGENT_CONFIG = {
    "portfolio_manager": {
        "name": "Portfolio Manager",
        "role": "Portfolio Manager",
        "avatar": "pm",
        "is_team_role": True,
    },
    "risk_manager": {
        "name": "Risk Manager",
        "role": "Risk Manager",
        "avatar": "risk",
        "is_team_role": True,
    },
    "sentiment_analyst": {
        "name": "Sentiment Analyst",
        "role": "Sentiment Analyst",
        "avatar": "sentiment",
        "is_team_role": False,
    },
    "technical_analyst": {
        "name": "Technical Analyst",
        "role": "Technical Analyst",
        "avatar": "technical",
        "is_team_role": False,
    },
    "fundamentals_analyst": {
        "name": "Fundamentals Analyst",
        "role": "Fundamentals Analyst",
        "avatar": "fundamentals",
        "is_team_role": False,
    },
    "valuation_analyst": {
        "name": "Valuation Analyst",
        "role": "Valuation Analyst",
        "avatar": "valuation",
        "is_team_role": False,
    },
}

ANALYST_TYPES = {
    "fundamentals_analyst": {
        "display_name": "Fundamentals Analyst",
        "agent_id": "fundamentals_analyst",
        "description": "Uses LLM to intelligently select analysis tools, focuses on financial data and company fundamental analysis",
        "order": 12,
    },
    "technical_analyst": {
        "display_name": "Technical Analyst",
        "agent_id": "technical_analyst",
        "description": "Uses LLM to intelligently select analysis tools, focuses on technical indicators and chart analysis",
        "order": 11,
    },
    "sentiment_analyst": {
        "display_name": "Sentiment Analyst",
        "agent_id": "sentiment_analyst",
        "description": "Uses LLM to intelligently select analysis tools, analyzes market sentiment and news sentiment",
        "order": 13,
    },
    "valuation_analyst": {
        "display_name": "Valuation Analyst",
        "agent_id": "valuation_analyst",
        "description": "Uses LLM to intelligently select analysis tools, focuses on company valuation and value assessment",
        "order": 14,
    },
    # "comprehensive_analyst": {
    #     "display_name": "Comprehensive Analyst",
    #     "agent_id": "comprehensive_analyst",
    #     "description": "Uses LLM to intelligently select analysis tools, performs comprehensive analysis",
    #     "order": 15
    # }
}
