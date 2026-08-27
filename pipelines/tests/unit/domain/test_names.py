import pytest

from app.domain.names import bayer_aliases, parse_bayer, search_key


@pytest.mark.parametrize(
    "a,b",
    [
        ("Rosaliadecastro", "Rosalíadecastro"),  # real exoplanet-host match
        ("ϵ Her", "ε Her"),  # lunate epsilon, NFKC-dependent
        ("Uñallamacha", "Unallamacha"),
        ("BATSŨ̀", "Batsu"),
    ],
)
def test_search_key_folds_equivalent_forms(a, b) -> None:
    assert search_key(a) == search_key(b)


def test_variable_star_is_not_treated_as_bayer() -> None:
    assert parse_bayer("V5652 Sgr").kind == "variable"
    assert bayer_aliases(parse_bayer("V5652 Sgr")) == []


def test_flamsteed_number_recognised() -> None:
    assert parse_bayer("6 Equ").kind == "flamsteed"


def test_greek_and_latin_forms_produce_same_aliases() -> None:
    def keys(s: str) -> set[str]:
        return {search_key(a) for a in bayer_aliases(parse_bayer(s))}

    assert keys("del Equ") == keys("δ Equ")


def test_component_is_preserved() -> None:
    parts = parse_bayer("ε1 Lyr A")
    assert parts.component == "A" and parts.superscript == "1"
