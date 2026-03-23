# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Extract API server sidecar.
#
# Build with:
#   pyinstaller api_server.spec
#
# Output: dist/api-server/  (one-directory bundle)
#
# After building, the build script copies this directory to
# desktop/src-tauri/binaries/api-server/ for Tauri to bundle.

from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / "api_server_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Ship the LLM prompts, schemas, configs, and project template
        (str(ROOT / "prompts"),           "prompts"),
        (str(ROOT / "schemas"),           "schemas"),
        (str(ROOT / "configs"),           "configs"),
        (str(ROOT / "_project_template"), "_project_template"),
    ],
    hiddenimports=[
        # ── App modules (passed as strings to uvicorn, not auto-detected) ──
        "api",
        "api.main",
        "api.routers",
        "api.routers.projects",
        "api.routers.ingest",
        "api.routers.analyze",
        "api.routers.reports",
        "api.routers.export",
        "api.routers.settings",
        "api.routers.activate",
        "engine",
        "engine.core",
        "engine.core.document_loader",
        "engine.core.llm_router",
        "engine.core.paths",
        "engine.models",
        "engine.market",
        "engine.market.live_prices",
        "engine.llm",
        "engine.llm.extraction",
        "engine.llm.extraction.extract_project_facts",
        "engine.llm.extraction.extract_economic_assumptions",
        "engine.llm.extraction.extract_mine_plan_inputs",
        "engine.llm.extraction.gather_market_intelligence",
        "engine.llm.reporting",
        "engine.llm.reporting.write_geology_section",
        "engine.llm.reporting.write_economics_section",
        "engine.llm.reporting.write_risk_section",
        "engine.llm.reporting.assemble_report_sections",
        "engine.llm.providers",
        "engine.llm.providers.router",
        "engine.llm.providers.openai_client",
        "engine.llm.providers.anthropic_client",
        "engine.llm.prompt_loader",
        "engine.llm.response",
        "engine.llm.dual_runner",
        "engine.economics",
        "engine.economics.dcf_model",
        "engine.economics.input_builder",
        "engine.economics.sensitivity_runner",
        # yfinance + dependencies
        "yfinance",
        "yfinance.base",
        "yfinance.ticker",
        "pandas",
        "numpy",
        "requests",
        "lxml",
        "lxml.etree",
        # ── uvicorn internals — not auto-detected
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.off",
        "uvicorn.lifespan.on",
        # FastAPI / Starlette
        "fastapi",
        "starlette",
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        # Pydantic
        "pydantic",
        "pydantic.deprecated.class_validators",
        # Multipart (file uploads)
        "multipart",
        "python_multipart",
        # HTTP clients (OpenAI / Anthropic)
        "httpx",
        "httpx._transports",
        "anyio",
        "anyio._backends._asyncio",
        # AI SDKs
        "openai",
        "anthropic",
        "tiktoken",
        "tiktoken_ext",
        "tiktoken_ext.openai_public",
        # Document parsing
        "fitz",        # pymupdf
        "pymupdf",
        "openpyxl",
        "docx",
        "ezdxf",
        "ezdxf.addons",
        "ezdxf.addons.drawing",
        # Charting (CAD render)
        "matplotlib",
        "matplotlib.backends.backend_agg",
        # PDF export
        "fpdf",
        "fpdf.fonts",
        # Data
        "polars",
        # Email (used internally by some libs)
        "email.mime",
        "email.mime.multipart",
        "email.mime.text",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "test",
        "unittest",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="api-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,   # UPX can break some C-extension modules — leave off
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name="api-server",
)
