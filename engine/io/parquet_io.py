"""
Parquet I/O utilities using Polars.

All reads and writes go through Polars for consistency with the rest of
the engine's DataFrame layer. Snappy compression is used by default as
it provides a good balance of speed and compression ratio for the
tabular data this platform handles (drillhole tables, assay data, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def read_parquet(path: Path | str) -> pl.DataFrame:
    """
    Read a Parquet file into a Polars DataFrame.

    Parameters
    ----------
    path:
        Path to the Parquet file.

    Returns
    -------
    pl.DataFrame
    """
    return pl.read_parquet(Path(path))


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_parquet(
    df: pl.DataFrame,
    path: Path | str,
    *,
    compression: str = "snappy",
) -> None:
    """
    Write a Polars DataFrame to a Parquet file.

    Creates parent directories if they do not exist.

    Parameters
    ----------
    df:
        DataFrame to write.
    path:
        Destination file path.
    compression:
        Parquet compression codec. Defaults to "snappy".
        Other options: "zstd", "lz4", "gzip", "brotli", "uncompressed".
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path, compression=compression)


# ---------------------------------------------------------------------------
# Append
# ---------------------------------------------------------------------------

def append_parquet(
    df: pl.DataFrame,
    path: Path | str,
    *,
    compression: str = "snappy",
) -> None:
    """
    Append rows to an existing Parquet file.

    Reads the existing file, concatenates *df*, and writes back.
    If the file does not exist, it is created.

    The schemas of the existing file and *df* must be compatible
    (same column names and types). Mismatched columns will raise
    a Polars error.

    Parameters
    ----------
    df:
        DataFrame whose rows to append.
    path:
        Path to the Parquet file.
    compression:
        Compression codec for the written file.
    """
    path = Path(path)
    if path.exists():
        existing = read_parquet(path)
        combined = pl.concat([existing, df], how="diagonal")
    else:
        combined = df
    write_parquet(combined, path, compression=compression)


# ---------------------------------------------------------------------------
# Convenience converters
# ---------------------------------------------------------------------------

def parquet_to_dicts(path: Path | str) -> list[dict[str, Any]]:
    """
    Read a Parquet file and return its rows as a list of dicts.

    Parameters
    ----------
    path:
        Path to the Parquet file.

    Returns
    -------
    list[dict]
        One dict per row; keys are column names.
    """
    df = read_parquet(path)
    return df.to_dicts()


def dicts_to_parquet(
    records: list[dict[str, Any]],
    path: Path | str,
    *,
    compression: str = "snappy",
) -> None:
    """
    Write a list of dicts to a Parquet file.

    Polars infers the schema from the first record. All records must
    have the same keys; values may be None.

    Parameters
    ----------
    records:
        List of row dicts.
    path:
        Destination file path.
    compression:
        Compression codec.
    """
    if not records:
        # Write an empty DataFrame rather than failing
        df = pl.DataFrame()
    else:
        df = pl.from_dicts(records)
    write_parquet(df, path, compression=compression)


# ---------------------------------------------------------------------------
# Schema / inspection helpers
# ---------------------------------------------------------------------------

def parquet_schema(path: Path | str) -> dict[str, str]:
    """
    Return the column names and their Polars dtype strings for a Parquet file.

    Does not load the full dataset — reads only the file metadata.
    """
    path = Path(path)
    # Use Polars lazy scan to avoid loading data
    lf = pl.scan_parquet(path)
    return {name: str(dtype) for name, dtype in zip(lf.columns, lf.dtypes)}


def parquet_row_count(path: Path | str) -> int:
    """Return the number of rows in a Parquet file without loading all data."""
    return pl.scan_parquet(Path(path)).collect().height
