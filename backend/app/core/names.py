"""Name folding primitives.

Must stay behaviourally identical to pipelines/app/names.py. The contract is
pinned by tests/test_search_key_contract.py, which exists in both projects.
"""

from __future__ import annotations

import unicodedata

_APOSTROPHE_LIKE = frozenset("\u02bb\u02bc\u2018\u2019'")


def search_key(text: str) -> str:
    """Fold a name to a comparison key.

    NFKC before NFKD is required: it folds U+03F5 LUNATE EPSILON to U+03B5,
    which the 'ϵ Her' row in IAU-CSN depends on.
    """
    normalised = unicodedata.normalize("NFKC", text)
    decomposed = unicodedata.normalize("NFKD", normalised)
    stripped = "".join(
        c for c in decomposed if not unicodedata.combining(c) and c not in _APOSTROPHE_LIKE
    )
    return "".join(c for c in stripped.casefold() if c.isalnum())
