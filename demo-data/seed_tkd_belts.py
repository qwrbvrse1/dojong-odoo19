"""
seed_tkd_belts.py
=================
Run via Odoo shell:

    sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
      shell -c /etc/odoo19.conf -d prod --shell-interface python \
      < /opt/odoo19/odoo19/custom-addons/demo-data/seed_tkd_belts.py

WHAT IT DOES
------------
1. Prints all existing martial art styles + programs (discovery phase).
2. Finds or creates a "Taekwondo" martial art style (code="TKD").
3. Creates the standard WT (World Taekwondo) belt rank system — 10 color belts
   (White → Red/Black Stripe) + 5 Dan levels — if they don't already exist.
4. Links all created belt ranks to any programs whose style is Taekwondo
   (via the belt_rank_ids many2many on dojo.program).
5. Commits.

SET DRY_RUN = True to preview without writing.
"""

# ── CONFIG ────────────────────────────────────────────────────────────────────
DRY_RUN = False
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("DISCOVERY — Martial Art Styles & Programs")
print("=" * 60)

styles = env['dojo.martial.art.style'].search([])
for s in styles:
    print(f"  Style  id={s.id}  code={s.code!r}  name={s.name!r}  belt_count={s.belt_count}")

programs = env['dojo.program'].search([])
for p in programs:
    sname = p.style_id.name if p.style_id else "(no style)"
    print(f"  Program  id={p.id}  name={p.name!r}  style={sname!r}  existing_belts={len(p.belt_rank_ids)}")

# ── Standard WT / World Taekwondo belt system ─────────────────────────────────
# (name, sequence, hex_color, attendance_threshold, max_stripes, is_dan, dan_level)
TKD_BELTS = [
    ("White Belt",                10, "#ffffff",  0,  0, False, 0),
    ("Yellow Belt",               20, "#f9c800",  15, 3, False, 0),
    ("Yellow Belt / Green Stripe",30, "#c8e06e",  20, 3, False, 0),
    ("Green Belt",                40, "#2e7d32",  25, 3, False, 0),
    ("Green Belt / Blue Stripe",  50, "#5c9dcc",  30, 3, False, 0),
    ("Blue Belt",                 60, "#1565c0",  35, 3, False, 0),
    ("Blue Belt / Red Stripe",    70, "#944c99",  40, 3, False, 0),
    ("Red Belt",                  80, "#c62828",  50, 3, False, 0),
    ("Red Belt / Black Stripe",   90, "#7b1c1c",  60, 3, False, 0),
    ("Recommended Black Belt",   100, "#3d2b2b",  70, 0, False, 0),
    # Dan grades
    ("1st Dan — Black Belt",     110, "#212121", 100, 0, True,  1),
    ("2nd Dan — Black Belt",     120, "#212121", 150, 0, True,  2),
    ("3rd Dan — Black Belt",     130, "#212121", 200, 0, True,  3),
    ("4th Dan — Black Belt",     140, "#212121", 250, 0, True,  4),
    ("5th Dan — Black Belt (Master)", 150, "#212121", 300, 0, True, 5),
]

# ── Phase 1: find / create TKD style ─────────────────────────────────────────
print("\n" + "=" * 60)
print(f"PHASE 1 — {'[DRY RUN] ' if DRY_RUN else ''}Taekwondo Martial Art Style")
print("=" * 60)

Style = env['dojo.martial.art.style']
tkd_style = Style.search([('code', '=', 'TKD')], limit=1)
if not tkd_style:
    tkd_style = Style.search([('name', 'ilike', 'taekwondo')], limit=1)

if tkd_style:
    print(f"  FOUND existing style: id={tkd_style.id}  name={tkd_style.name!r}")
else:
    if DRY_RUN:
        print("  WOULD CREATE style: name='Taekwondo'  code='TKD'")
        tkd_style = None
    else:
        tkd_style = Style.create({
            'name': 'Taekwondo',
            'code': 'TKD',
            'description': 'Korean martial art focusing on kicks and striking techniques.',
        })
        print(f"  CREATED style: id={tkd_style.id}  name={tkd_style.name!r}")

# ── Phase 2: create belt ranks ────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"PHASE 2 — {'[DRY RUN] ' if DRY_RUN else ''}Creating Taekwondo Belt Ranks")
print("=" * 60)

BeltRank = env['dojo.belt.rank']
Company = env['res.company'].search([], limit=1)

created_ranks = []

for (bname, seq, color, threshold, max_stripes, is_dan, dan_level) in TKD_BELTS:
    domain = [('name', '=', bname), ('style_id', '=', tkd_style.id if tkd_style else False)]
    existing = BeltRank.search(domain, limit=1)
    if existing:
        print(f"  SKIP (exists): {bname!r} id={existing.id}")
        created_ranks.append(existing)
        continue

    vals = {
        'name': bname,
        'sequence': seq,
        'color': color,
        'attendance_threshold': threshold,
        'max_stripes': max_stripes,
        'is_dan': is_dan,
        'dan_level': dan_level,
        'active': True,
        'company_id': Company.id,
    }
    if tkd_style and not DRY_RUN:
        vals['style_id'] = tkd_style.id

    if DRY_RUN:
        print(f"  WOULD CREATE: seq={seq:3d}  {bname!r}  color={color}  "
              f"threshold={threshold}  stripes={max_stripes}"
              + ("  [DAN]" if is_dan else ""))
        created_ranks.append(bname)  # placeholder
    else:
        rank = BeltRank.create(vals)
        created_ranks.append(rank)
        print(f"  CREATED id={rank.id}  seq={seq:3d}  {bname!r}")

print(f"\nTotal belt ranks: {len(created_ranks)}")

# ── Phase 3: assign per-program belt paths ────────────────────────────────────
#
# Per-program rules (inferred from program purpose + student age/level):
#   Pee Wee            — White → Green (4 ranks, youngest kids)
#   Children Beginners — White → Green/Blue Stripe (5 ranks)
#   Children Advance   — White → Recommended Black Belt (full 10 color belts)
#   All Beginners      — White → Yellow/Green Stripe (3 ranks, absolute beginners)
#   All Belts          — White → Recommended Black Belt (full 10 color belts)
#   Black Belt         — Dan grades only (5 ranks)
#   Black Belt Club    — Dan grades only (5 ranks)
#
print("\n" + "=" * 60)
print(f"PHASE 3 — {'[DRY RUN] ' if DRY_RUN else ''}Assigning per-program belt paths")
print("=" * 60)

# Build name → rank record lookup from DB
if not DRY_RUN and tkd_style:
    all_tkd_ranks = env['dojo.belt.rank'].search([('style_id', '=', tkd_style.id)])
    rank_by_name = {r.name: r for r in all_tkd_ranks}
else:
    rank_by_name = {name: name for (name, *_) in TKD_BELTS}

COLOR_BELTS = [
    "White Belt",
    "Yellow Belt",
    "Yellow Belt / Green Stripe",
    "Green Belt",
    "Green Belt / Blue Stripe",
    "Blue Belt",
    "Blue Belt / Red Stripe",
    "Red Belt",
    "Red Belt / Black Stripe",
    "Recommended Black Belt",
]
DAN_BELTS = [
    "1st Dan — Black Belt",
    "2nd Dan — Black Belt",
    "3rd Dan — Black Belt",
    "4th Dan — Black Belt",
    "5th Dan — Black Belt (Master)",
]

PROGRAM_BELT_MAP = {
    "Pee Wee":             COLOR_BELTS[:4],   # White → Green
    "Children Beginners":  COLOR_BELTS[:5],   # White → Green/Blue Stripe
    "Children Advance":    COLOR_BELTS,        # White → Recommended Black Belt
    "All Beginners":       COLOR_BELTS[:3],   # White → Yellow/Green Stripe
    "All Belts":           COLOR_BELTS,        # White → Recommended Black Belt
    "Black Belt":          DAN_BELTS,
    "Black Belt Club":     DAN_BELTS,
}

if tkd_style:
    tkd_programs = env['dojo.program'].search([('style_id', '=', tkd_style.id)])
    for prog in tkd_programs:
        belt_names = PROGRAM_BELT_MAP.get(prog.name)
        if belt_names is None:
            print(f"  SKIP {prog.name!r} — not in PROGRAM_BELT_MAP, leaving unchanged")
            continue

        ranks = [rank_by_name[n] for n in belt_names if n in rank_by_name]
        missing = [n for n in belt_names if n not in rank_by_name]
        if missing:
            print(f"  WARNING: ranks not found for {prog.name!r}: {missing}")

        if DRY_RUN:
            print(f"  WOULD SET {prog.name!r} → {belt_names[0]} … {belt_names[-1]} "
                  f"({len(ranks)} ranks)")
        else:
            prog.belt_rank_ids = [(6, 0, [r.id for r in ranks])]
            print(f"  SET {prog.name!r} → {belt_names[0]} … {belt_names[-1]} "
                  f"({len(ranks)} ranks)")
else:
    print("  Skipped (TKD style not available).")

# ── Commit ────────────────────────────────────────────────────────────────────
if DRY_RUN:
    env.cr.rollback()
    print("\n[DRY RUN] Rolled back. Set DRY_RUN = False to apply.")
else:
    env.cr.commit()
    print("\nAll changes committed successfully.")

print("=" * 60 + "\n")
quit()
