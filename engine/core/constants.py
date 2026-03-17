"""
System-wide constants.

These are values that are fixed by design, not configuration.
Tunable values belong in configs/global/app.yaml instead.
"""

from pathlib import Path

# Schema version — increment when normalized data structures change
SCHEMA_VERSION = "1.0.0"

# Engine version
ENGINE_VERSION = "0.1.0"

# Default encoding for all text files written by the engine
TEXT_ENCODING = "utf-8"

# Parquet compression used for all .parquet files written by the engine
PARQUET_COMPRESSION = "snappy"

# Name of the project metadata file inside normalized/metadata/
PROJECT_METADATA_FILENAME = "project_metadata.json"

# Name of the source registry file inside normalized/metadata/
SOURCE_REGISTRY_FILENAME = "source_manifest.json"

# Name of the data assessments file written by the critic
DATA_ASSESSMENTS_FILENAME = "data_assessments.json"

# Name of the run config file inside each run folder
RUN_CONFIG_FILENAME = "config.yaml"

# Folder name for run logs
RUNS_FOLDER = "runs"

# Prompt file extension
PROMPT_EXT = ".md"

# Maximum tokens to send in a single LLM context window (conservative default)
# Individual provider configs in configs/llm/ may override per model
DEFAULT_MAX_TOKENS = 128_000

# Chunk size for document splitting (in characters)
DEFAULT_CHUNK_SIZE = 4_000

# Overlap between chunks (in characters)
DEFAULT_CHUNK_OVERLAP = 400

# Supported raw file extensions by category
RAW_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".md"}
RAW_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
RAW_CAD_EXTENSIONS = {".dwg", ".dxf", ".obj", ".stl", ".gltf", ".glb", ".omf"}
RAW_GIS_EXTENSIONS = {".shp", ".geojson", ".gpkg", ".kml", ".kmz", ".tif", ".tiff"}
RAW_CSV_EXTENSIONS = {".csv", ".tsv"}
RAW_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

ALL_SUPPORTED_EXTENSIONS = (
    RAW_DOCUMENT_EXTENSIONS
    | RAW_IMAGE_EXTENSIONS
    | RAW_CAD_EXTENSIONS
    | RAW_GIS_EXTENSIONS
    | RAW_CSV_EXTENSIONS
    | RAW_VIDEO_EXTENSIONS
)
