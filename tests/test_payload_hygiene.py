"""H5: payload hygiene.

The trigger of every variant is what the model sees.  It must not carry a
key or a word that labels the attack (``inject``, ``attack``, ``poison``,
``swap``, ``forged``, ``falsif``, ``adversar``, ``malicious``) outside canary
text, and every variant must have a well-formed ``meta`` block.

Variants listed in ``tests/payload_hygiene_waivers.json`` still contain
such fields after the mechanical migration (their alert text describes
the attack instead of looking like an alert).  They are expected failures
until the STOP-gated rewrite lands; a waived variant that becomes clean
fails the test so the waiver is removed.
"""

import json
from pathlib import Path

import pytest

from attacks.migrate_payload_schema import hygiene_hits
from attacks.payload_schema import load_variants, validate_payload
from config import BASE_DIR

DOMAINS = ("cyberops", "healthcare", "finance", "legal")
WAIVERS = json.loads((BASE_DIR / "tests" / "payload_hygiene_waivers.json").read_text())["waivers"]


def _all_variants():
    for domain in DOMAINS:
        for ap in range(1, 16):
            for v in load_variants(domain, f"ap{ap}"):
                yield domain, f"ap{ap}", v


CASES = [(d, ap, v) for d, ap, v in _all_variants()]
IDS = [f"{d}/{v['variant_id']}" for d, ap, v in CASES]


@pytest.mark.parametrize("domain,ap,variant", CASES, ids=IDS)
def test_meta_block_is_well_formed(domain, ap, variant):
    assert validate_payload(variant, domain=domain) == []


@pytest.mark.parametrize("domain,ap,variant", CASES, ids=IDS)
def test_trigger_carries_no_attack_labels(domain, ap, variant):
    key = f"{domain}/{variant['variant_id']}"
    hits = hygiene_hits(variant.get("trigger", {}), variant["meta"].get("canaries", []))
    if key in WAIVERS:
        assert hits, f"{key} is clean now: remove it from payload_hygiene_waivers.json"
        pytest.xfail(f"waived until rewrite: {hits[:3]}")
    assert hits == [], hits


def test_meta_is_never_handed_to_the_host():
    from attacks.payload_schema import split_payload
    v = CASES[0][2]
    trigger, meta = split_payload(v)
    assert "meta" not in trigger and meta is not None
    assert not any(k.startswith("meta") for k in trigger)


def test_waiver_count_is_reported():
    """Keeps the number visible in the test output."""
    print(f"\nhygiene waivers: {len(WAIVERS)} variants")
    assert len(WAIVERS) <= 107
