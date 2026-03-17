"""
CSV I/O utilities using Polars.

Handles reading CSV files into Polars DataFrames with automatic delimiter
detection and column name normalisation.

Delimiter detection supports the four most common field separators used in
mining data exports: comma, tab, semicolon, and pipe.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import polars as pl


# ---------------------------------------------------------------------------
# Delimiter detection
# ---------------------------------------------------------------------------

_CANDIDATE_DELIMITERS = [",", "\t", ";", "|"]


def detect_delimiter(path: Path | str, *, sample_bytes: int = 8192) -> str:
    """
    Sniff the delimiter used in a CSV file.

    Reads up to *sample_bytes* from the file and uses :class:`csv.Sniffer`
    to detect the separator. Falls back to a frequency count across the
    four candidate delimiters if Sniffer cannot decide.

    Parameters
    ----------
    path:
        Path to the CSV (or delimited text) file.
    sample_bytes:
        Number of bytes to read as the sniff sample. Default 8 KiB.

    Returns
    -------
    str
        One of ``","``, ``"\\t"``, ``";"`` or ``"|"``.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        sample = fh.read(sample_bytes)

    # Try csv.Sniffer first
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters="".join(_CANDIDATE_DELIMITERS))
        if dialect.delimiter in _CANDIDATE_DELIMITERS:
            return dialect.delimiter
    except csv.Error:
        pass

    # Fallback: pick the delimiter that appears most in the sample
    counts = {d: sample.count(d) for d in _CANDIDATE_DELIMITERS}
    return max(counts, key=lambda d: counts[d])


# ---------------------------------------------------------------------------
# Column name normalisation
# ---------------------------------------------------------------------------

def normalise_column_names(df: pl.DataFrame) -> pl.DataFrame:
    """
    Return *df* with normalised column names.

    Normalisation steps:
    1. Strip leading/trailing whitespace
    2. Convert to lowercase
    3. Replace internal spaces (and multiple spaces) with underscores
    4. Remove any characters that are not alphanumeric or underscores

    Parameters
    ----------
    df:
        Input DataFrame.

    Returns
    -------
    pl.DataFrame
        DataFrame with renamed columns.
    """
    import re

    new_names: dict[str, str] = {}
    for col in df.columns:
        clean = col.strip().lower()
        clean = re.sub(r"\s+", "_", clean)
        clean = re.sub(r"[^\w]", "_", clean)
        clean = re.sub(r"_+", "_", clean).strip("_")
        new_names[col] = clean or col  # Never produce an empty column name

    return df.rename(new_names)


# ---------------------------------------------------------------------------
# Core read functions
# ---------------------------------------------------------------------------

def read_csv(
    path: Path | str,
    *,
    separator: str | None = None,
    encoding: str = "utf-8",
    **kwargs: Any,
) -> pl.DataFrame:
    """
    Read a CSV file into a Polars DataFrame.

    Auto-detects the delimiter if *separator* is not provided.

    Parameters
    ----------
    path:
        Path to the CSV file.
    separator:
        Field delimiter. If None, :func:`detect_delimiter` is called.
    encoding:
        File encoding. Defaults to UTF-8. For Latin-1 / Windows-1252
        files commonly produced by mining software, pass ``"latin-1"``.
    **kwargs:
        Additional keyword arguments forwarded to :func:`polars.read_csv`.
        Common options: ``has_header``, ``null_values``, ``infer_schema_length``.

    Returns
    -------
    pl.DataFrame
    """
    path = Path(path)
    if separator is None:
        separator = detect_delimiter(path)

    # Polars read_csv accepts separator; handle encoding via bytes
    if encoding.lower() in ("utf-8", "utf8"):
        return pl.read_csv(path, separator=separator, **kwargs)
    else:
        # Read as bytes after decoding, then feed to Polars via StringIO
        raw = path.read_bytes().decode(encoding, errors="replace")
        return pl.read_csv(
            io.StringIO(raw).read().encode("utf-8"),
            separator=separator,
            **kwargs,
        )


def read_csv_normalised(
    path: Path | str,
    *,
    separator: str | None = None,
    encoding: str = "utf-8",
    **kwargs: Any,
) -> pl.DataFrame:
    """
    Read a CSV file and normalise its column names.

    Combines :func:`read_csv` and :func:`normalise_column_names`.

    Parameters
    ----------
    path:
        Path to the CSV file.
    separator:
        Field delimiter (auto-detected if None).
    encoding:
        File encoding. Defaults to UTF-8.
    **kwargs:
        Forwarded to :func:`read_csv`.

    Returns
    -------
    pl.DataFrame
        DataFrame with normalised column names.
    """
    df = read_csv(path, separator=separator, encoding=encoding, **kwargs)
    return normalise_column_names(df)


# ---------------------------------------------------------------------------
# Convenience converter
# ---------------------------------------------------------------------------

def csv_to_dicts(
    path: Path | str,
    *,
    normalise_columns: bool = True,
    separator: str | None = None,
    encoding: str = "utf-8",
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Read a CSV file and return its rows as a list of dicts.

    Parameters
    ----------
    path:
        Path to the CSV file.
    normalise_columns:
        If True (default), column names are normalised before conversion.
    separator:
        Field delimiter (auto-detected if None).
    encoding:
        File encoding.
    **kwargs:
        Forwarded to :func:`read_csv`.

    Returns
    -------
    list[dict]
        One dict per row; keys are (optionally normalised) column names.
    """
    if normalise_columns:
        df = read_csv_normalised(path, separator=separator, encoding=encoding, **kwargs)
    else:
        df = read_csv(path, separator=separator, encoding=encoding, **kwargs)
    return df.to_dicts()
