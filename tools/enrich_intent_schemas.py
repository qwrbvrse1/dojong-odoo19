#!/usr/bin/env python3
"""
Bulk Intent Schema Enricher
============================
Reads all intents from ai_intent_schema_data.xml, uses OpenAI to generate
10 varied example phrases per intent, and writes an enriched output file.

Usage:
    OPENAI_API_KEY=sk-... python tools/enrich_intent_schemas.py

    # Then review the diff and apply if satisfied:
    cp addons/dojo_assistant/data/ai_intent_schema_data_enriched.xml \
       addons/dojo_assistant/data/ai_intent_schema_data.xml

    # After updating the XML, update the module:
    docker compose run --rm web -u dojo_assistant -d odoo19 \
        --config=/etc/odoo/odoo.conf --stop-after-init
"""

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests

# ── Config ────────────────────────────────────────────────────────────────────
SCHEMA_FILE = os.path.join(
    os.path.dirname(__file__),
    "../addons/dojo_assistant/data/ai_intent_schema_data.xml",
)
OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__),
    "../addons/dojo_assistant/data/ai_intent_schema_data_enriched.xml",
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"
EXAMPLES_PER_INTENT = 10
DELAY_BETWEEN_CALLS = 0.5  # seconds, to avoid rate limits


# ── OpenAI helper ─────────────────────────────────────────────────────────────

def generate_examples(intent_type, description, current_examples):
    """Ask OpenAI to generate realistic example phrases for an intent."""
    current_str = "\n".join(f"  - {e}" for e in current_examples) if current_examples else "  (none)"
    prompt = (
        f"You are improving an AI assistant for a martial arts dojo.\n\n"
        f"Intent: {intent_type}\n"
        f"Description: {description}\n"
        f"Current examples:\n{current_str}\n\n"
        f"Generate {EXAMPLES_PER_INTENT} realistic, varied example phrases that a dojo instructor "
        f"or front-desk staff member might say to trigger this intent. "
        f"Cover different phrasings, levels of formality, and specificity. "
        f"Do NOT repeat or slightly rephrase the current examples. "
        f"Return ONLY a JSON array of strings, no explanation, no markdown."
    )

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    # Wrap in an object so JSON mode works (requires a top-level object)
    payload["messages"][0]["content"] += '\n\nRespond as: {"examples": [...]}'

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(raw)
    return data.get("examples", [])


# ── XML parsing helpers ───────────────────────────────────────────────────────

def get_field_value(record, field_name):
    """Return the text value of a <field name="field_name"> element."""
    for field in record.findall("field"):
        if field.get("name") == field_name:
            return (field.text or "").strip()
    return ""


def set_field_value(record, field_name, value):
    """Set the text value of a <field name="field_name"> element (creates if missing)."""
    for field in record.findall("field"):
        if field.get("name") == field_name:
            field.text = value
            return
    # Create new field element
    new_field = ET.SubElement(record, "field")
    new_field.set("name", field_name)
    new_field.text = value


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("Usage: OPENAI_API_KEY=sk-... python tools/enrich_intent_schemas.py")
        sys.exit(1)

    if not os.path.exists(SCHEMA_FILE):
        print(f"ERROR: Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)

    print(f"Reading: {SCHEMA_FILE}")
    tree = ET.parse(SCHEMA_FILE)
    root = tree.getroot()

    intent_records = [
        r for r in root.findall(".//record")
        if r.get("model") == "dojo.ai.intent.schema"
    ]
    print(f"Found {len(intent_records)} intent schema records.\n")

    total = len(intent_records)
    for i, record in enumerate(intent_records, 1):
        intent_type = get_field_value(record, "intent_type")
        description = get_field_value(record, "description")
        current_examples_raw = get_field_value(record, "example_phrases")
        current_examples = [
            line.strip("- ").strip()
            for line in current_examples_raw.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        print(f"[{i}/{total}] {intent_type} ({len(current_examples)} existing examples)")

        try:
            new_examples = generate_examples(intent_type, description, current_examples)
        except Exception as e:
            print(f"  WARNING: Failed to generate examples for {intent_type}: {e}")
            continue

        # Merge: keep existing + add new ones (deduplicated, case-insensitive)
        existing_lower = {e.lower() for e in current_examples}
        merged = list(current_examples)
        added = 0
        for ex in new_examples:
            ex = ex.strip()
            if ex and ex.lower() not in existing_lower:
                merged.append(ex)
                existing_lower.add(ex.lower())
                added += 1

        print(f"  + {added} new examples (total: {len(merged)})")

        # Write back as newline-separated list
        merged_str = "\n".join(f"- {e}" for e in merged)
        set_field_value(record, "example_phrases", "\n" + merged_str + "\n")

        time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\nWriting enriched file: {OUTPUT_FILE}")
    # Preserve XML declaration
    tree.write(OUTPUT_FILE, encoding="unicode", xml_declaration=False)

    # Prepend the XML declaration and odoo wrapper if original had it
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("<?xml"):
        content = '<?xml version="1.0" encoding="utf-8"?>\n' + content

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("\nDone! Review the enriched file, then apply it:")
    print(f"  cp {OUTPUT_FILE} {SCHEMA_FILE}")
    print()
    print("Then update the module:")
    print("  docker compose run --rm web -u dojo_assistant -d odoo19 \\")
    print("      --config=/etc/odoo/odoo.conf --stop-after-init")


if __name__ == "__main__":
    main()
