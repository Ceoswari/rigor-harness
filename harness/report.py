"""The two output surfaces: machine-readable state and a human handoff."""
import json
import os
from typing import Dict

LABEL_ORDER = ["conflicting", "indeterminate", "distinct", "reinforcing", "unrelated"]


def write_json(run: Dict, verification: Dict, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = dict(run)
    payload["source"] = {k: v for k, v in run["source"].items() if k != "text"}
    payload["verification"] = verification
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    return path


def write_markdown(run: Dict, verification: Dict, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    src = run["source"]
    lines = []
    lines.append("# Rigor harness run")
    lines.append("")
    status = "VERIFIED" if verification["verified"] else "NOT VERIFIED"
    lines.append("**Status:** %s" % status)
    lines.append("")
    lines.append("## Source")
    lines.append("")
    lines.append("- URL: %s" % src["url"])
    if src.get("fetch_mode") == "offline_fixture":
        lines.append("- Loaded: %s from saved copy `%s` (no network request)"
                     % (src["last_seen_at"], src.get("fixture_path")))
    else:
        lines.append("- Fetched: %s (HTTP %s)" % (src["last_seen_at"], src["http_status"]))
    lines.append("- Content SHA-256: `%s`" % src["content_sha256"][:16])
    lines.append("- Revision count: %s" % src.get("revision_count"))
    lines.append("")
    lines.append("## Extracted claims (%d)" % len(run["claims"]))
    lines.append("")
    for claim in run["claims"]:
        quals = (" [%s]" % ", ".join(claim["qualifiers"])) if claim["qualifiers"] else ""
        lines.append("- **%s** (%s, polarity %+d)%s: %s"
                     % (claim["claim_id"], claim["axis"], claim["polarity"], quals,
                        claim["text"]))
    lines.append("")
    lines.append("## Comparisons")
    lines.append("")
    ordered = sorted(run["comparisons"],
                     key=lambda c: LABEL_ORDER.index(c["classification"])
                     if c["classification"] in LABEL_ORDER else 99)
    for comp in ordered:
        lines.append("### %s: %s" % (comp["reference_id"], comp["classification"].upper()))
        lines.append("")
        lines.append("> %s" % comp["reference_statement"])
        lines.append("")
        lines.append("%s" % comp["rationale"])
        if comp.get("evidence"):
            lines.append("")
            lines.append("Evidence (%s): %s"
                         % (comp["evidence"]["claim_id"], comp["evidence"]["source_sentence"]))
        lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append(verification["summary"])
    lines.append("")
    for check in verification["checks"]:
        lines.append("- [%s] **%s** %s" % ("PASS" if check["passed"] else "FAIL",
                                           check["check"], check["detail"]))
    lines.append("")
    lines.append("## Material limitations")
    lines.append("")
    for note in run.get("limitations", []):
        lines.append("- %s" % note)
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path
