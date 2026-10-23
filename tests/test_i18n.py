"""English and Hindi UI strings stay in sync."""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "app/static/js/i18n.js").read_text()


def keys(lang):
    block = re.search(rf"\n  {lang}: \{{(.*?)\n  \}},", SRC, re.S).group(1)
    return set(re.findall(r"(\w+):\s*\"", block))


def test_same_keys_in_both_languages():
    en, hi = keys("en"), keys("hi")
    assert en and en == hi, (en ^ hi)


def test_hindi_strings_are_devanagari():
    block = re.search(r"\n  hi: \{(.*?)\n  \},", SRC, re.S).group(1)
    vals = re.findall(r":\s*\"([^\"]*)\"", block)
    deva = [v for v in vals if re.search(r"[ऀ-ॿ]", v)]
    assert len(deva) / len(vals) > 0.85
