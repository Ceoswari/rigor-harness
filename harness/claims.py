"""Claim extraction and normalisation into comparable propositions.

The comparison problem in this pilot has a specific shape worth naming.
Reference A ("tracing is enabled by default") and Reference B ("tracing is
disabled by default") share every content word but one. Any similarity- or
keyword-based comparator scores them as near-identical and will call B
supporting evidence. The only thing that separates them is polarity on a
shared predicate axis.

So claims are normalised to (subject, axis, polarity, qualifiers) and compared
on that structure rather than on surface overlap.
"""
import re
from typing import Dict, List, Optional, Set

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "by",
    "for", "of", "to", "in", "on", "at", "it", "its", "this", "that", "these",
    "those", "and", "or", "but", "as", "with", "from", "you", "your", "can",
    "will", "may", "if", "when", "which", "there", "their", "they", "we",
}

# Predicate axes. Each axis is a pair of opposed states; matching on the axis
# with opposite polarity is what surfaces a conflict.
AXES = {
    "enablement": ({"enabled", "enable", "on", "active", "turned-on"},
                   {"disabled", "disable", "off", "inactive", "turned-off"}),
    "inclusion": ({"included", "includes", "captured", "recorded", "present"},
                  {"excluded", "excludes", "omitted", "redacted", "absent"}),
    "requirement": ({"required", "mandatory", "must"},
                    {"optional", "unnecessary"}),
    "truth": ({"true"}, {"false"}),
}

QUALIFIERS = {
    "by_default": re.compile(r"\bby default\b|\bdefaults? to\b", re.I),
    "globally": re.compile(r"\bglobal(ly)?\b", re.I),
    "per_run": re.compile(r"\bper[- ]run\b|\bindividual runs?\b", re.I),
}

NEGATIONS = re.compile(r"\b(not|never|no longer|cannot|can't|isn't|aren't)\b", re.I)


def split_sentences(text: str) -> List[str]:
    """Cheap sentence split. Docs pages are not prose, so newlines count."""
    chunks: List[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z`])", line):
            piece = piece.strip()
            if piece:
                chunks.append(piece)
    return chunks


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower())]


def content_tokens(text: str) -> Set[str]:
    return {t for t in tokenize(text) if t not in STOPWORDS and len(t) > 1}


def classify_axis(tokens: Set[str]) -> Optional[Dict]:
    """Find which predicate axis a claim sits on, and on which side."""
    for axis, (positive, negative) in AXES.items():
        if tokens & positive:
            return {"axis": axis, "polarity": 1, "marker": sorted(tokens & positive)[0]}
        if tokens & negative:
            return {"axis": axis, "polarity": -1, "marker": sorted(tokens & negative)[0]}
    return None


def normalize(sentence: str) -> Optional[Dict]:
    """Turn one sentence into a proposition, or None if it states no claim."""
    tokens = content_tokens(sentence)
    axis_hit = classify_axis(tokens)
    if axis_hit is None:
        return None

    polarity = axis_hit["polarity"]
    if NEGATIONS.search(sentence):
        polarity *= -1

    axis_words = set()
    for positive, negative in AXES.values():
        axis_words |= positive | negative

    subject = tokens - axis_words - {"default", "defaults"}
    quals = sorted(name for name, pat in QUALIFIERS.items() if pat.search(sentence))

    return {
        "text": sentence.strip(),
        "subject": sorted(subject),
        "axis": axis_hit["axis"],
        "polarity": polarity,
        "marker": axis_hit["marker"],
        "qualifiers": quals,
    }


def materiality(prop: Dict, focus_terms: Set[str]) -> float:
    """Rank claims so a bounded set can be taken.

    Acceptance test 3 asks for a small set of material claims rather than a
    dump of the page, so extraction needs an ordering, not just a filter.
    """
    subject = set(prop["subject"])
    score = 0.0
    score += 3.0 * len(subject & focus_terms)
    score += 1.5 * len(prop["qualifiers"])
    if 3 <= len(subject) <= 12:
        score += 1.0
    if len(prop["text"]) > 300:
        score -= 2.0
    return score


def extract(text: str, focus_terms: Set[str], limit: int = 8) -> List[Dict]:
    """Extract a bounded, ranked set of material claims from source text."""
    seen: Set[str] = set()
    props: List[Dict] = []
    for sentence in split_sentences(text):
        if len(sentence) < 15 or len(sentence) > 400:
            continue
        prop = normalize(sentence)
        if prop is None:
            continue
        key = (prop["axis"], prop["polarity"], tuple(prop["subject"]))
        if key in seen:
            continue
        seen.add(str(key))
        prop["materiality"] = materiality(prop, focus_terms)
        props.append(prop)
    props.sort(key=lambda p: p["materiality"], reverse=True)
    for i, prop in enumerate(props[:limit]):
        prop["claim_id"] = "clm_%02d" % (i + 1)
    return props[:limit]
