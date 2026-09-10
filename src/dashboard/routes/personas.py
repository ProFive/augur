"""Persona list, detail, opinion, and custom-persona CRUD routes.

Extracted from dashboard/app.py (router split R4).
Mounts via: app.include_router(personas_router)
"""

import logging
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from augur.config import get_config
from augur.personas.base import MarketContext
from dashboard.deps import get_registry
import dashboard.deps as _deps

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Persona enrichment metadata ----

PERSONA_ENRICHMENT = {
    "buffett": {"cn_name": "沃伦·巴菲特", "en_name": "Warren Buffett", "school": "value", "core_principles": ["Economic moats determine long-term value", "Only buy businesses you understand", "Be greedy when others are fearful."], "holdings": ["BRK.B", "AAPL", "KO", "AXP"]},
    "graham": {"cn_name": "本杰明·格雷厄姆", "en_name": "Benjamin Graham", "school": "value", "core_principles": ["Margin of safety is the cornerstone of investing", "Mr. Market is moody", "Buy stocks below net asset value"], "holdings": ["GEICO", "BRK.B"]},
    "munger": {"cn_name": "查理·芒格", "en_name": "Charlie Munger", "school": "value", "core_principles": ["Multiple mental models", "Buy quality businesses at reasonable prices", "Avoiding stupidity is more important than seeking brilliance"], "holdings": ["BRK.B", "COST", "BAC"]},
    "fisher": {"cn_name": "菲利普·费雪", "en_name": "Philip Fisher", "school": "growth", "core_principles": ["The real value of growth stocks lies in management", "Deep research through casual conversations", "Hold high-quality growth stocks for the long term"], "holdings": ["MOTOROLA", "TXN"]},
    "lynch": {"cn_name": "彼得·林奇", "en_name": "Peter Lynch", "school": "growth", "core_principles": ["Find tenbaggers in everyday life", "PEG is the core of growth stock valuation", "Diversify but focus on what you understand"], "holdings": ["SBUX", "FNM"]},
    "cathie_wood": {"cn_name": "凯瑟琳·伍德", "en_name": "Cathie Wood", "school": "growth", "core_principles": ["Disruptive innovation creates exponential growth", "5-year investment horizon", "Embrace volatility"], "holdings": ["TSLA", "COIN", "ROKU", "SQ"]},
    "aschenbrenner": {"cn_name": "利奥波德·阿申布伦纳", "en_name": "Leopold Aschenbrenner", "school": "growth", "core_principles": ["The AI supercycle is coming", "Computing power is the new oil", "AGI will reshape all industries"], "holdings": ["NVDA", "MSFT", "GOOGL"]},
    "thiel": {"cn_name": "彼得·蒂尔", "en_name": "Peter Thiel", "school": "growth", "core_principles": ["Only monopoly companies have real value", "Going from 0 to 1 is more important than from 1 to N", "Discover secrets through contrarian thinking"], "holdings": ["PLTR", "META", "TSLA"]},
    "dalio": {"cn_name": "瑞·达利欧", "en_name": "Ray Dalio", "school": "macro", "core_principles": ["Understand that the debt cycle drives everything", "All-weather portfolio to cope with uncertainty", "Radical transparency and principled decision-making"], "holdings": ["SPY", "GLD", "TLT"]},
    "soros": {"cn_name": "乔治·索罗斯", "en_name": "George Soros", "school": "macro", "core_principles": ["Reflexivity: cognition affects reality", "Shoot first, aim later", "Identify market mispricings"], "holdings": ["MACRO_BETS"]},
    "marks": {"cn_name": "霍华德·马克斯", "en_name": "Howard Marks", "school": "macro", "core_principles": ["Cycles are the most certain thing in investing", "Risk comes from overpricing", "Contrarian investing requires courage"], "holdings": ["OAK", "HY_BONDS"]},
    "serenity": {"cn_name": "宁静", "en_name": "Serenity", "school": "quant", "core_principles": ["Volatility is a manageable risk", "Tail risk hedging protects capital", "Systematically eliminate emotional interference"], "holdings": ["VIX_HEDGE", "OPTIONS"]},
    "arps": {"cn_name": "马丁·阿普斯", "en_name": "Martin Arps", "school": "quant", "core_principles": ["Prices contain all information", "The trend is your friend", "Volume-price divergence is the strongest signal"], "holdings": ["TECH_MOMENTUM"]},
    "dayu": {"cn_name": "大宇", "en_name": "Dayu", "school": "quant", "core_principles": ["Quantitative models eliminate subjective bias", "Capital flows reveal the intentions of major players", "Statistical arbitrage seeks certainty"], "holdings": ["A_SHARES"]},
    "duan_yongping": {"cn_name": "段永平", "en_name": "Duan Yongping", "school": "china", "core_principles": ["Do the right thing, stop doing the wrong thing", "Business model is more important than anything", "Extremely concentrated holdings"], "holdings": ["AAPL", "PDD", "BABA"]},
    "zhang_lei": {"cn_name": "张磊", "en_name": "Zhang Lei", "school": "china", "core_principles": ["Long-term structural value creation", "Research-driven investment", "Grow together with great companies"], "holdings": ["PDD", "JD", "BYD"]},
    "li_lu": {"cn_name": "李录", "en_name": "Li Lu", "school": "china", "core_principles": ["Value investing is equally applicable in China", "Understand the evolution of civilization", "Concentrate investment in a few certain opportunities"], "holdings": ["BRK.B", "BYD", "BABA"]},
    "dan_bin": {"cn_name": "但斌", "en_name": "Dan Bin", "school": "china", "core_principles": ["The rose of time: long-termism", "Consumer leaders are the best track", "Long slopes and thick snow compound interest is amazing"], "holdings": ["600519.SS", "AAPL", "MOUTAI"]},
}


def _persona_meta() -> List[Dict]:
    registry = get_registry()
    config = get_config()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    meta = []
    for agent in registry.get_all():
        chinese_investors = {"duan_yongping", "zhang_lei", "li_lu", "dan_bin", "dayu"}
        country = "\U0001f1e8\U0001f1f3 中国" if agent.agent_id in chinese_investors else ""
        enrichment = PERSONA_ENRICHMENT.get(agent.agent_id, {})
        is_custom = (custom_dir / f"{agent.agent_id}.yaml").exists()
        meta.append({
            "id": agent.agent_id,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "cn_name": enrichment.get("cn_name", agent.name),
            "en_name": enrichment.get("en_name", agent.name),
            "school": enrichment.get("school", "value"),
            "core_principles": enrichment.get("core_principles", agent.philosophy[:3] if agent.philosophy else []),
            "holdings": enrichment.get("holdings", []),
            "style": " · ".join(agent.philosophy[:2]) if agent.philosophy else "",
            "description": agent.identity.strip().replace("\n", " ").replace("  ", " "),
            "scenarios": agent.philosophy,
            "scoring_weights": agent.scoring_weights if agent.scoring_weights else {},
            "weight": f"{list(agent.scoring_weights.values())[0]:.0%}" if agent.scoring_weights else "均等",
            "status": "已注册",
            "country": country,
            "is_chinese": agent.agent_id in chinese_investors,
            "chip_name": (
                enrichment.get("en_name", agent.name)
                if agent.agent_id in chinese_investors
                else enrichment.get("en_name", agent.name).split()[-1]
            ),
            "is_custom": is_custom,
            "quote": agent.philosophy[0] if agent.philosophy else "Investing is investing in the future.",
            "model": per_agent.get(agent.agent_id, default_model),
        })
    return meta


# ---- Request models ----

class CustomPersonaBody(BaseModel):
    """Request body for custom persona creation."""
    yaml_content: str
    agent_id: str


# ---- Routes ----

@router.get("/api/personas", summary="Get a list of all investors.")
async def list_personas():
    """Return a list of all investor personas."""
    registry = get_registry()
    return {
        "status": "ok",
        "count": len(registry.get_all()),
        "personas": [agent.to_dict() for agent in registry.get_all()],
    }


@router.get("/api/persona/compare", summary="Compare the views of two investors on the same target")
def compare_personas(persona1: str, persona2: str, ticker: str):
    """
    Compare the analysis views of two investors on the same target.

    Note: fetch_market_context is a synchronous function that calls yfinance synchronously. Using async def would block the event loop.
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    registry = get_registry()
    agent1 = registry.get(persona1)
    agent2 = registry.get(persona2)

    if not agent1:
        raise HTTPException(status_code=404, detail=f"Persona '{persona1}' not found")
    if not agent2:
        raise HTTPException(status_code=404, detail=f"Persona '{persona2}' not found")

    ctx = MarketContext(ticker=ticker.upper())
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        pass

    try:
        resp1 = agent1.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {persona1}: {e}")

    try:
        resp2 = agent2.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {persona2}: {e}")

    enrichment1 = PERSONA_ENRICHMENT.get(persona1, {})
    enrichment2 = PERSONA_ENRICHMENT.get(persona2, {})

    def _build_result(agent_id, agent, resp, enrichment):
        return {
            "agent_id": agent_id,
            "agent_name": enrichment.get("cn_name", agent.name),
            "en_name": enrichment.get("en_name", agent.name),
            "school": enrichment.get("school", ""),
            "signal": resp.signal.value,
            "score": round(resp.score, 1),
            "confidence": round(resp.confidence, 2),
            "reasoning": resp.reasoning,
            "key_findings": resp.key_findings,
            "risks": resp.risks if hasattr(resp, "risks") else [],
        }

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "persona1": _build_result(persona1, agent1, resp1, enrichment1),
        "persona2": _build_result(persona2, agent2, resp2, enrichment2),
        "agreement": resp1.signal == resp2.signal,
        "score_diff": round(abs(resp1.score - resp2.score), 1),
    }


@router.get("/api/persona/{agent_id}", summary="Get details of a single investor")
async def get_persona(agent_id: str):
    """Get detailed information of a single investor"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")
    return agent.to_dict()


@router.get("/api/persona/{agent_id}/opinion", summary="Get a single investor's analysis on a target")
def get_persona_opinion(agent_id: str, ticker: str, question: Optional[str] = None):
    """
    Use a single investor to analyze the specified target and return their independent view.

    Note: fetch_market_context is a synchronous function that calls yfinance synchronously. Using async def would block the event loop.
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    if question is not None and len(question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 characters).")

    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")

    ctx = MarketContext(ticker=ticker.upper())
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        pass

    try:
        response = agent.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    enrichment = PERSONA_ENRICHMENT.get(agent_id, {})

    return {
        "status": "ok",
        "agent_id": agent_id,
        "agent_name": enrichment.get("cn_name", agent.name),
        "ticker": ticker.upper(),
        "signal": response.signal.value,
        "score": round(response.score, 1),
        "confidence": round(response.confidence, 2),
        "reasoning": response.reasoning,
        "key_findings": response.key_findings,
        "risks": response.risks if hasattr(response, "risks") else [],
        "question": question,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@router.post("/api/custom-persona", summary="Create a custom investor")
async def api_create_custom_persona(body: CustomPersonaBody):
    """Save custom Persona YAML to personas/custom/"""
    if not re.match(r'^[a-z0-9_-]+$', body.agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id: only lowercase letters, digits, hyphens, and underscores are allowed",
        )
    if len(body.agent_id) > 50:
        raise HTTPException(status_code=400, detail="agent_id too long (max 50 characters)")
    if '..' in body.agent_id:
        raise HTTPException(status_code=400, detail="agent_id contains invalid characters")
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML content: {e}")
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    filepath = custom_dir / f"{body.agent_id}.yaml"
    filepath.write_text(body.yaml_content, encoding="utf-8")

    try:
        from augur.persona_loader import load_persona_yaml
        new_agent = load_persona_yaml(str(filepath))
        with _deps._singleton_init_lock:
            if _deps._registry is not None and new_agent.agent_id not in {a.agent_id for a in _deps._registry.get_all()}:
                _deps._registry.register(new_agent)
                _deps._coordinator = None
    except Exception:
        pass

    return {"status": "ok", "path": str(filepath), "hot_loaded": True}


@router.get("/api/custom-personas", summary="List all custom investors")
async def api_list_custom_personas():
    """List all custom investors in the personas/custom/ directory"""
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    personas = []
    for fp in sorted(custom_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
            personas.append({
                "agent_id": data.get("agent_id", fp.stem),
                "name": data.get("name", fp.stem),
                "filepath": str(fp),
            })
        except Exception:
            personas.append({
                "agent_id": fp.stem,
                "name": fp.stem,
                "filepath": str(fp),
            })
    return {"status": "ok", "personas": personas}


@router.delete("/api/custom-persona/{agent_id}", summary="Delete a custom investor")
async def api_delete_custom_persona(agent_id: str):
    """Delete the custom investor YAML in personas/custom/ and unregister from the registry"""
    if not re.match(r'^[a-z0-9_-]+$', agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    filepath = custom_dir / f"{agent_id}.yaml"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Custom persona '{agent_id}' not found")
    filepath.unlink()
    with _deps._singleton_init_lock:
        if _deps._registry is not None:
            try:
                _deps._registry.unregister(agent_id)
                _deps._coordinator = None
            except Exception:
                pass
    return {"status": "ok", "agent_id": agent_id, "message": "Deleted custom persona and unregistered from registry."}


@router.put("/api/custom-persona/{agent_id}", summary="Update a custom investor")
async def api_update_custom_persona(agent_id: str, body: CustomPersonaBody):
    """Update an existing custom investor YAML and hot reload into the registry"""
    if not re.match(r'^[a-z0-9_-]+$', agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    filepath = custom_dir / f"{agent_id}.yaml"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Custom persona '{agent_id}' not found")
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML content: {e}")
    filepath.write_text(body.yaml_content, encoding="utf-8")
    try:
        from augur.persona_loader import load_persona_yaml
        new_agent = load_persona_yaml(str(filepath))
        with _deps._singleton_init_lock:
            if _deps._registry is not None:
                try:
                    _deps._registry.unregister(agent_id)
                except Exception:
                    pass
                _deps._registry.register(new_agent)
                _deps._coordinator = None
    except Exception:
        pass
    return {"status": "ok", "agent_id": agent_id, "path": str(filepath), "hot_loaded": True}
