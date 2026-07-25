"""Name and designation normalisation.

Verified against the 606-row IAU-CSN snapshot. Every rule here exists because
the real data required it - see the docstring notes for the specific rows.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from re import Match
from typing import cast

# Apostrophe-like marks that must fold away for search but stay in display names.
# (No 'okina in the current snapshot, but retained: WGSN adds Polynesian names.)
_APOSTROPHE_LIKE = frozenset("\u02bb\u02bc\u2018\u2019'")

# Greek letter -> canonical lowercase Latin abbreviation (the 24 letters).
GREEK_TO_ABBREV = {
    "α": "alf",
    "β": "bet",
    "γ": "gam",
    "δ": "del",
    "ε": "eps",
    "ζ": "zet",
    "η": "eta",
    "θ": "the",
    "ι": "iot",
    "κ": "kap",
    "λ": "lam",
    "μ": "mu",
    "ν": "nu",
    "ξ": "xi",
    "ο": "omi",
    "π": "pi",
    "ρ": "rho",
    "σ": "sig",
    "τ": "tau",
    "υ": "ups",
    "φ": "phi",
    "χ": "chi",
    "ψ": "psi",
    "ω": "ome",
}
# Spelled-out English name -> same abbreviation (rows like 'Iota Her')
SPELLED_TO_ABBREV = {
    "alpha": "alf",
    "beta": "bet",
    "gamma": "gam",
    "delta": "del",
    "epsilon": "eps",
    "zeta": "zet",
    "eta": "eta",
    "theta": "the",
    "iota": "iot",
    "kappa": "kap",
    "lambda": "lam",
    "mu": "mu",
    "nu": "nu",
    "xi": "xi",
    "omicron": "omi",
    "pi": "pi",
    "rho": "rho",
    "sigma": "sig",
    "tau": "tau",
    "upsilon": "ups",
    "phi": "phi",
    "chi": "chi",
    "psi": "psi",
    "omega": "ome",
}
ABBREV_TO_GREEK = {v: k for k, v in GREEK_TO_ABBREV.items()}

# GCVS variable-star designations (V#####) are NOT Bayer letters.
_VARIABLE_STAR = re.compile(r"^V\d+$")


def search_key(text: str) -> str:
    """Fold a name to a comparison key. Display names keep their original form.

    NFKC (not NFKD) is required: it folds U+03F5 LUNATE EPSILON to U+03B5,
    which the 'ϵ Her' row depends on.
    """
    normalised = unicodedata.normalize("NFKC", text)
    decomposed = unicodedata.normalize("NFKD", normalised)
    stripped = "".join(
        c for c in decomposed if not unicodedata.combining(c) and c not in _APOSTROPHE_LIKE
    )
    return "".join(c for c in stripped.casefold() if c.isalnum())


@dataclass(frozen=True, slots=True)
class BayerParts:
    """A parsed Bayer/Flamsteed designation. ``kind`` records what it actually is."""

    kind: str  # 'bayer' | 'flamsteed' | 'variable' | 'unparsed'
    letter: str | None  # canonical abbreviation, e.g. 'alf'
    superscript: str | None  # '1' in 'γ1 Del'
    constellation: str | None  # as written ('Cyg' or 'Bootis')
    component: str | None  # 'A' in 'ε1 Lyr A'
    raw: str


def parse_bayer(raw: str) -> BayerParts:
    """Parse the mixed encodings found in IAU-CSN's 'Bayer ID' column."""
    text = unicodedata.normalize("NFKC", raw).strip()
    if not text:
        return BayerParts("unparsed", None, None, None, None, raw)

    tokens = text.split()
    head = tokens[0]
    constellation = tokens[1] if len(tokens) > 1 else None
    component = tokens[2] if len(tokens) > 2 else None

    # V5652 Sgr -> variable star, not Bayer
    if _VARIABLE_STAR.match(head):
        return BayerParts("variable", None, None, constellation, component, raw)

    # 6 Equ, 109 Virginis -> Flamsteed number
    if head.isdigit():
        return BayerParts("flamsteed", head, None, constellation, component, raw)

    # split trailing superscript digits: 'γ1' -> 'γ','1'   'alf01' -> 'alf','01'
    match = cast(Match[str], re.match(r"^(.*?)(\d*)$", head))
    base, superscript = match.group(1), match.group(2) or None

    letter = (
        GREEK_TO_ABBREV.get(base)
        or SPELLED_TO_ABBREV.get(base.casefold())
        or (base.casefold() if base.casefold() in ABBREV_TO_GREEK else None)
    )
    kind = "bayer" if letter else "unparsed"
    return BayerParts(kind, letter, superscript, constellation, component, raw)


def bayer_aliases(parts: BayerParts) -> list[str]:
    """Generate searchable alias forms for a parsed designation.

    Middle path: Greek symbol <-> Latin abbreviation <-> spelled-out name.
    Constellation genitive expansion is deliberately NOT done here.
    """
    if parts.kind != "bayer" or not parts.letter or not parts.constellation:
        return []
    sup = parts.superscript or ""
    greek = ABBREV_TO_GREEK.get(parts.letter, "")
    spelled = next((k for k, v in SPELLED_TO_ABBREV.items() if v == parts.letter), parts.letter)
    forms = [
        f"{greek}{sup} {parts.constellation}",
        f"{parts.letter}{sup} {parts.constellation}",
        f"{spelled.capitalize()}{sup} {parts.constellation}",
    ]
    if parts.component:
        forms = [f"{f} {parts.component}" for f in forms]
    return [f for f in forms if f.strip()]
