"""HTML page routes: all browser-facing GET endpoints that render templates."""

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from augur.config import get_config
from augur.workspace import get_workspace, resolve_landing_url
from dashboard.deps import get_registry, templates
from dashboard.routes.personas import _persona_meta

router = APIRouter()


@router.get("/", response_class=HTMLResponse, summary="Home Dashboard")
async def index(request: Request):
    landing = resolve_landing_url(get_workspace(), path="/")
    if landing:
        return RedirectResponse(url=landing, status_code=302)
    agent_count = len(get_registry().get_all())
    try:
        from augur.datasources import available_sources
        ds_count = len(available_sources())
    except Exception:
        ds_count = 2
    stats = [
        {"value": str(agent_count), "label": "Virtual Investment Guru", "icon": "users"},
        {"value": "6", "label": "Consensus Weighting Layer", "icon": "layers"},
        {"value": "40+", "label": "Scoring Factors", "icon": "sliders"},
        {"value": str(ds_count), "label": "Data Source Links", "icon": "database"},
    ]
    featured = [
        {"avatar": "🏦", "id": "buffett", "name": "Warren Buffett", "style": "Value · Moat", "desc": "Seek companies with enduring competitive advantages and hold them for the long term at reasonable prices. Free Cash Flow (FCF) and Return on Equity (ROE) are the core metrics.", "tag": "Value investing"},
        {"avatar": "📐", "id": "graham", "name": "Benjamin Graham", "style": "Margin of Safety · Cigarette Stocks", "desc": "Only buy when there is a significant margin of safety, with hard thresholds of PE<15 and PB<1.5.", "tag": "Deep Value"},
        {"avatar": "🚀", "id": "cathie_wood", "name": "Cathie Wood", "style": "Disruptive Innovation", "desc": "Focuses on disruptive technologies such as AI, genomics, and blockchain, accepting high valuations for exponential growth.", "tag": "Growth investing"},
        {"avatar": "🇨🇳", "id": "duan_yongping", "name": "段永平", "style": "Conscientious · Highly Concentrated", "desc": "The \"Conscientious\" philosophy: only do the right things and stop doing the wrong things. Highly concentrated holdings within the circle of competence.", "tag": "China Value"},
    ]
    return templates.TemplateResponse(request=request, name="index.html", context={
        "title": "Augur — Master Investor Dashboard",
        "agent_count": agent_count,
        "stats": stats,
        "featured": featured,
    })


@router.get("/personas", response_class=HTMLResponse, summary="Investor Personas Page")
async def personas_page(request: Request):
    return templates.TemplateResponse(request=request, name="personas.html", context={
        "personas": _persona_meta(),
        "title": "Investor Personas",
    })


@router.get("/stocks", response_class=HTMLResponse, summary="Stock Analysis Page")
async def stocks_page(request: Request):
    # quick_tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "BRK.B", "META", "AMZN", "PDD", "BIDU"] 
    quick_tickers = ["FPT.VN", "HPG.VN", "VCB.VN", "VIC.VN", "VHM.VN", "VNM.VN", "MSN.VN", "VRE.VN", "VJC.VN", "MWG.VN"] # vietnam market
    return templates.TemplateResponse(request=request, name="stocks.html", context={
        "title": "Stock Analysis",
        "quick_tickers": quick_tickers,
    })


@router.get("/signals", response_class=HTMLResponse, summary="Signals Monitoring Page")
async def signals_page(request: Request):
    return templates.TemplateResponse(request=request, name="signals.html", context={
        "title": "Signals Monitoring",
    })


@router.get("/scanner", response_class=HTMLResponse, summary="Market Scanner Page")
async def scanner_page(request: Request):
    return templates.TemplateResponse(request=request, name="scanner.html", context={
        "title": "Market Scanner - Scanner",
    })


@router.get("/watchlist", response_class=HTMLResponse, summary="Watchlist Page")
async def watchlist_page(request: Request):
    return templates.TemplateResponse(request=request, name="watchlist.html", context={
        "title": "Watchlist - Watchlist",
    })


@router.get("/portfolio", response_class=HTMLResponse, summary="Portfolio Management Page")
async def portfolio_page(request: Request):
    return templates.TemplateResponse(request=request, name="portfolio.html", context={
        "title": "Portfolio Management - Portfolio",
    })


@router.get("/settings", response_class=HTMLResponse, summary="Settings Page")
async def settings_page(request: Request):
    config = get_config()
    available_models = config.get("available_models", {})
    models_flat = []
    for provider_models in available_models.values():
        if isinstance(provider_models, list):
            models_flat.extend(provider_models)
    personas = _persona_meta()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    for p in personas:
        p["current_model"] = per_agent.get(p["id"], default_model)
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "title": "Settings",
        "personas": personas,
        "available_models": models_flat,
        "default_model": default_model,
    })


@router.get("/create-persona", response_class=HTMLResponse, summary="Create Custom Investor Page")
async def create_persona_page(request: Request):
    return templates.TemplateResponse(request=request, name="create_persona.html", context={
        "title": "Create Custom Investor",
    })


@router.get("/report/{ticker}", response_class=HTMLResponse, summary="Deep Analysis Report Full-Page")
async def report_view_page(request: Request, ticker: str):
    """Dedicated full-page report view for a ticker. Auto-fetches report on load."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")
    return templates.TemplateResponse(request=request, name="report_view.html", context={
        "title": f"{ticker.upper()} Deep Analysis Report - Augur",
        "ticker": ticker.upper(),
    })
