#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed the probe user for S1 gate verification."""

# Seed the probe user (internal, no dojo groups)
User = env['res.users']
probe = User.search([('login', '=', 'probe@qa.local')], limit=1)

vals = {
    'name': 'QA Probe User',
    'login': 'probe@qa.local',
    'password': 'Probe-2026!',
    'active': True,
}

if probe:
    probe.write(vals)
    print(f"Updated probe user: {probe.login} (id={probe.id})")
else:
    probe = User.create(vals)
    print(f"Created probe user: {probe.login} (id={probe.id})")

# Ensure ONLY base.group_user is set
group_user_id = env.ref('base.group_user').id
dojo_admin_id = env.ref('dojo_core.group_dojo_admin', raise_if_not_found=False)
dojo_instructor_id = env.ref('dojo_core.group_dojo_instructor', raise_if_not_found=False)
dojo_parent_id = env.ref('dojo_core.group_dojo_parent_student', raise_if_not_found=False)

# Remove all dojo groups if present
env.cr.execute("""
    DELETE FROM res_groups_users_rel
    WHERE uid = %s AND gid IN %s
""", (probe.id, tuple(filter(None, [dojo_admin_id and dojo_admin_id.id,
                                      dojo_instructor_id and dojo_instructor_id.id,
                                      dojo_parent_id and dojo_parent_id.id])) or (0,)))

# Ensure base.group_user is present
env.cr.execute("""
    INSERT INTO res_groups_users_rel (uid, gid)
    VALUES (%s, %s)
    ON CONFLICT DO NOTHING
""", (probe.id, group_user_id))

print(f"Probe user configured with base.group_user only")
env.cr.commit()
