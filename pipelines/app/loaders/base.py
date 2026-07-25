"""Shared helpers for source loaders."""

from __future__ import annotations

import re

import polars as pl

_TAG = re.compile(r"<[^>]*>")


def strip_tags(text: str) -> str:
    return _TAG.sub("", text).strip()


def clean_headers(df: pl.DataFrame) -> pl.DataFrame:
    """Remove HTML wrappers and surrounding whitespace from column names."""
    return df.rename({c: strip_tags(c) for c in df.columns})
