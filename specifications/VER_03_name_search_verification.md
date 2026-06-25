# VER-03: Verify dojo_core name_search — surname ranking confirmed via live RPC

## Objective

Verify that the `dojo.member._name_search` method correctly implements surname-first ranking when searching for members. Specifically, when a user searches for a partial name like "Smi", members whose **last name** starts with "Smi" should be ranked **above** members who have "Smi" elsewhere in their name.

## Background

REL-001 INC-03 implemented surname-first ranking in `dojo.member._name_search()` to improve member lookup UX. The implementation parses the search query to extract the probable surname (last token), then partitions matching records into two groups:
1. Members whose `last_name` starts with the probable surname
2. All other matches

The method returns surname matches first, followed by other matches.

This verification increment confirms the implementation works correctly against the running Odoo instance.

## Test Data

Demo data file `addons/dojo_core/data/demo_members.xml` defines four test members:

| Name | First Name | Last Name | Expected Ranking for "Smi" |
|------|-----------|-----------|---------------------------|
| Jane Smith | Jane | Smith | **High** (surname match) |
| Jordan Smith | Jordan | Smith | **High** (surname match) |
| Smith Jones | Smith | Jones | Low (first name match) |
| John Smithson | John | Smithson | Low (surname partial) |

## Gate Script

`testenv/scripts/ver03-name-search.sh`:

1. Authenticates to the running Odoo instance (http://127.0.0.1:8070)
2. Calls `dojo.member.name_search("Smi")` via JSON-RPC
3. Verifies:
   - At least one result is returned
   - Surname matches (Jane Smith, Jordan Smith) appear **before** non-surname matches (Smith Jones, John Smithson)
   - If both groups are present, validates positional ordering
4. Exits 0 on success, non-zero on failure

## Implementation Notes

### Code Location

`addons/dojo_core/models/member.py:254-297` — `_name_search()` override

### Algorithm

1. Parse search query to extract tokens
2. Last token is treated as probable surname
3. Fetch all records matching the base search domain
4. Partition results:
   - `surname_matches`: records where `last_name.lower().startswith(probable_surname.lower())`
   - `other_matches`: all other records
5. Return `surname_matches + other_matches`, respecting the `limit` parameter

### Edge Cases

- Single-token query (e.g., "Smith"): treated as surname
- Multi-token query (e.g., "Jane Smi"): last token ("Smi") is treated as surname
- Empty query or non-ilike operators: falls back to `super()._name_search()`
- No surname matches: returns all matches in original order

## Success Criteria

- Module `dojo_core` upgrades cleanly with demo data loaded
- Gate script exits 0
- Live RPC call returns results with correct surname-first ranking
- No ticket IDs in source files
- At least 3 files changed (demo data, manifest, test script, specification)

## Verification

Run the gate commands:

```bash
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http \
  -u dojo_core --stop-after-init

bash testenv/scripts/ver03-name-search.sh
```

Expected output from test script:
```
name_search returned 4 results in order:
  1. Jane Smith
  2. Jordan Smith
  3. Smith Jones
  4. John Smithson
✓ Surname-first ranking verified: surname matches ranked above non-surname matches
✓ name_search surname-first ranking: PASS
```

## Related Files

- `addons/dojo_core/models/member.py` — `_name_search()` implementation
- `addons/dojo_core/data/demo_members.xml` — test data
- `addons/dojo_core/__manifest__.py` — demo data registration
- `testenv/scripts/ver03-name-search.sh` — gate script
