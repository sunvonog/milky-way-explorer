"""Shared helpers for source loaders."""

from __future__ import annotations

import re

import polars as pl

_TAG = re.compile(r"<[^>]*>")

# Tokens the naming sources use to mean "no value". IAU-CSN writes '' and '--';
# WGSN_Faints writes '_' and '-'. Left as text they become junk identifiers such
# as 'HD _', which fold to the same search key as a real 'HD' prefix query.
PLACEHOLDER_TOKENS = frozenset({"", "_", "-", "--"})


def strip_tags(text: str) -> str:
    return _TAG.sub("", text).strip()


def clean_headers(df: pl.DataFrame) -> pl.DataFrame:
    """Remove HTML wrappers and surrounding whitespace from column names."""
    return df.rename({c: strip_tags(c) for c in df.columns})


def null_placeholders(
    df: pl.DataFrame, tokens: frozenset[str] = PLACEHOLDER_TOKENS
) -> pl.DataFrame:
    """Replace placeholder tokens with null in every string column."""
    listed = list(tokens)
    return df.with_columns(
        [
            pl.when(pl.col(name).str.strip_chars().is_in(listed))
            .then(None)
            .otherwise(pl.col(name))
            .alias(name)
            for name, dtype in df.schema.items()
            if dtype == pl.String
        ]
    )


def strip_catalogue_prefix(column: str, catalogue: str) -> pl.Expr:
    """Reduce a catalogue designation to its bare number ('HIP 1547' -> '1547').

    Sources disagree on whether the catalogue name is part of the value. Storing
    the bare number keeps a single join key; callers re-add the prefix for display.
    """
    return pl.col(column).str.replace(rf"(?i)^{catalogue}\s*", "")
