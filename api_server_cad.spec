# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — Extract CAD Analysis Pack.
#
# This builds a REPLACEMENT sidecar that includes everything in the base
# build PLUS the heavy CAD and Geology 3D dependencies:
#   - OCP / CADVERT      — STEP, IGES, BREP solid model analysis (~221MB)
#   - VTK / pyvista      — OMF block models, VTK volumes, OBJ/STL mesh (~380MB)
#
# Build:
#   pyinstaller api_server_cad.spec
#
# Output: dist/api-server-cad/
# Users who purchase the CAD pack replace their api-server/ directory with this one.
# The /capabilities endpoint will then return cad_pack: true and omf_pack: true.

from pathlib import Path

ROOT = Path(SPECPATH)
block_cipher = None

# Re-use the base spec's Analysis by importing it as a starting point,
# then add CAD-specific hidden imports on top.
_BASE_HIDDEN = [
    "api", "api.main", "api.routers",
    "api.routers.projects", "api.routers.ingest", "api.routers.analyze",
    "api.routers.reports", "api.routers.export", "api.routers.settings",
    "api.routers.activate", "api.routers.comparables", "api.routers.drillholes",
    "api.routers.llm", "api.routers.news", "api.routers.normalize",
    "api.routers.notes", "api.routers.npv", "api.routers.portfolio",
    "api.routers.renders", "api.routers.resources", "api.routers.review",
    "api.routers.royalties", "api.routers.tools", "api.routers.capabilities",
    "engine", "engine.core", "engine.core.document_loader", "engine.core.paths",
    "engine.core.capabilities",
    "engine.market", "engine.market.live_prices", "engine.market.fetch_project_news",
    "engine.market.jurisdiction_risk",
    "engine.llm", "engine.llm.extraction",
    "engine.llm.extraction.extract_project_facts",
    "engine.llm.extraction.extract_economic_assumptions",
    "engine.llm.extraction.extract_mine_plan_inputs",
    "engine.llm.extraction.extract_metallurgy",
    "engine.llm.extraction.extract_permitting",
    "engine.llm.extraction.extract_operator_track_record",
    "engine.llm.extraction.extract_capital_structure",
    "engine.llm.extraction.extract_cad_semantics",
    "engine.llm.extraction.extract_citations",
    "engine.llm.extraction.extract_comparable_transactions",
    "engine.llm.extraction.extract_resource_summary",
    "engine.llm.extraction.extract_resource_table",
    "engine.llm.extraction.extract_risks",
    "engine.llm.extraction.extract_royalties",
    "engine.llm.extraction.gather_market_intelligence",
    "engine.llm.extraction.research_jurisdiction_profile",
    "engine.llm.reporting",
    "engine.llm.reporting.write_geology_section",
    "engine.llm.reporting.write_economics_section",
    "engine.llm.reporting.write_risk_section",
    "engine.llm.reporting.assemble_report_sections",
    "engine.llm.reporting.write_cad_section",
    "engine.llm.reporting.write_executive_summary",
    "engine.llm.reporting.write_methodology",
    "engine.llm.providers",
    "engine.llm.providers.router",
    "engine.llm.providers.openai_client",
    "engine.llm.providers.anthropic_client",
    "engine.llm.prompt_loader", "engine.llm.response", "engine.llm.dual_runner",
    "engine.llm.tools", "engine.llm.tools.schemas", "engine.llm.tools.extractor",
    "engine.llm.tools.economics", "engine.llm.tools.executor",
    "engine.llm.tools.cad",
    "engine.economics", "engine.economics.dcf_model",
    "engine.economics.input_builder", "engine.economics.sensitivity_runner",
    "yfinance", "yfinance.base", "yfinance.ticker",
    "pandas", "numpy", "requests", "lxml", "lxml.etree",
    "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.loops.asyncio", "uvicorn.protocols", "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan", "uvicorn.lifespan.off", "uvicorn.lifespan.on",
    "fastapi", "starlette", "starlette.routing", "starlette.middleware",
    "starlette.middleware.cors",
    "pydantic", "pydantic.deprecated.class_validators",
    "multipart", "python_multipart",
    "httpx", "httpx._transports", "anyio", "anyio._backends._asyncio",
    "openai", "anthropic", "tiktoken", "tiktoken_ext", "tiktoken_ext.openai_public",
    "fitz", "pymupdf", "openpyxl", "docx", "ezdxf",
    "ezdxf.addons", "ezdxf.addons.drawing",
    "matplotlib", "matplotlib.backends.backend_agg",
    "fpdf", "fpdf.fonts",
    "polars",
    "email.mime", "email.mime.multipart", "email.mime.text",
]

_CAD_HIDDEN = [
    # CADVERT + OCC
    "cadvert",
    "cadvert.ingest", "cadvert.topology", "cadvert.geometry",
    "cadvert.features", "cadvert.spatial", "cadvert.document",
    "OCP", "OCP.BRep", "OCP.BRepExtrema", "OCP.BRepAdaptor",
    "OCP.BRepBndLib", "OCP.BRepBuilderAPI", "OCP.BRepTools",
    "OCP.BRepGProp", "OCP.GProp", "OCP.Geom", "OCP.GeomAbs",
    "OCP.GeomAdaptor", "OCP.TopAbs", "OCP.TopExp", "OCP.TopoDS",
    "OCP.TopTools", "OCP.gp", "OCP.STEPControl", "OCP.IGESControl",
    # VTK / pyvista / OMF
    "pyvista", "vtkmodules", "vtkmodules.all",
    "omf", "omf.base", "omf.data", "omf.elements",
    "pooch", "scooby",
]

a = Analysis(
    [str(ROOT / "api_server_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "prompts"),           "prompts"),
        (str(ROOT / "schemas"),           "schemas"),
        (str(ROOT / "configs"),           "configs"),
        (str(ROOT / "_project_template"), "_project_template"),
    ],
    hiddenimports=_BASE_HIDDEN + _CAD_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
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
    upx=False,
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
    name="api-server-cad",
)
