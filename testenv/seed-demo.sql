-- Seed demo data for VER tests
-- Creates: demo kiosk config, demo member, demo onboarding record

-- Create demo partner (dojo members require a res.partner)
INSERT INTO res_partner (name, company_id, active, type, autopost_bills, create_uid, write_uid, create_date, write_date)
VALUES ('Demo Member', 1, true, 'contact', 'ask', 1, 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create demo member
INSERT INTO dojo_member (name, partner_id, member_number, membership_state, create_uid, write_uid, create_date, write_date)
SELECT 'Demo Member', id, 'DEMO001', 'active', 1, 1, NOW(), NOW()
FROM res_partner
WHERE name = 'Demo Member'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Create demo kiosk config
INSERT INTO dojo_kiosk_config (name, pin_code, kiosk_token, theme_mode, view_mode, active, show_title, create_uid, write_uid, create_date, write_date)
VALUES ('Demo Kiosk', '1234', 'demo-token-12345', 'dark', 'search_only', true, true, 1, 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create demo onboarding record (if dojo_onboarding is installed)
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'dojo_onboarding_record') THEN
    INSERT INTO dojo_onboarding_record (
      member_id,
      state,
      step_member_info,
      step_household,
      step_enrollment,
      create_uid,
      write_uid,
      create_date,
      write_date
    )
    SELECT
      dm.id,
      'in_progress',
      true,
      true,
      false,
      1,
      1,
      NOW(),
      NOW()
    FROM dojo_member dm
    WHERE dm.name = 'Demo Member'
    ON CONFLICT DO NOTHING;
  END IF;
END $$;

-- Create demo program (required for class template)
INSERT INTO dojo_program (name, code, active, is_trial, create_uid, write_uid, create_date, write_date)
VALUES ('Demo Program', 'DEMO', true, false, 1, 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create demo class template
INSERT INTO dojo_class_template (
  name,
  code,
  program_id,
  level,
  duration_minutes,
  max_capacity,
  active,
  create_uid,
  write_uid,
  create_date,
  write_date
)
SELECT
  'Demo Class',
  'DEMO-CLASS',
  dp.id,
  'beginner',
  60,
  20,
  true,
  1,
  1,
  NOW(),
  NOW()
FROM dojo_program dp
WHERE dp.code = 'DEMO'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Create demo sessions for today (active, upcoming_soon, upcoming, done)
DO $$
DECLARE
  template_id_val integer;
BEGIN
  SELECT id INTO template_id_val FROM dojo_class_template WHERE code = 'DEMO-CLASS' LIMIT 1;

  IF template_id_val IS NOT NULL THEN
    -- Active session (started 30 min ago, ends in 30 min)
    INSERT INTO dojo_class_session (
      name,
      template_id,
      state,
      start_datetime,
      end_datetime,
      capacity,
      create_uid,
      write_uid,
      create_date,
      write_date
    )
    VALUES (
      'Demo Active Session',
      template_id_val,
      'open',
      NOW() - INTERVAL '30 minutes',
      NOW() + INTERVAL '30 minutes',
      20,
      1,
      1,
      NOW(),
      NOW()
    );

    -- Upcoming soon session (starts in 10 min)
    INSERT INTO dojo_class_session (
      name,
      template_id,
      state,
      start_datetime,
      end_datetime,
      capacity,
      create_uid,
      write_uid,
      create_date,
      write_date
    )
    VALUES (
      'Demo Upcoming Soon Session',
      template_id_val,
      'open',
      NOW() + INTERVAL '10 minutes',
      NOW() + INTERVAL '70 minutes',
      20,
      1,
      1,
      NOW(),
      NOW()
    );

    -- Upcoming session (starts in 3 hours)
    INSERT INTO dojo_class_session (
      name,
      template_id,
      state,
      start_datetime,
      end_datetime,
      capacity,
      create_uid,
      write_uid,
      create_date,
      write_date
    )
    VALUES (
      'Demo Upcoming Session',
      template_id_val,
      'open',
      NOW() + INTERVAL '3 hours',
      NOW() + INTERVAL '4 hours',
      20,
      1,
      1,
      NOW(),
      NOW()
    );

    -- Done session (ended 2 hours ago)
    INSERT INTO dojo_class_session (
      name,
      template_id,
      state,
      start_datetime,
      end_datetime,
      capacity,
      create_uid,
      write_uid,
      create_date,
      write_date
    )
    VALUES (
      'Demo Done Session',
      template_id_val,
      'done',
      NOW() - INTERVAL '3 hours',
      NOW() - INTERVAL '2 hours',
      20,
      1,
      1,
      NOW(),
      NOW()
    );
  END IF;
END $$;

-- Create demo enrollment for active session
DO $$
DECLARE
  member_id_val integer;
  session_id_val integer;
BEGIN
  SELECT id INTO member_id_val FROM dojo_member WHERE name = 'Demo Member' LIMIT 1;
  SELECT id INTO session_id_val FROM dojo_class_session WHERE name = 'Demo Active Session' LIMIT 1;

  IF member_id_val IS NOT NULL AND session_id_val IS NOT NULL THEN
    INSERT INTO dojo_class_enrollment (
      session_id,
      member_id,
      status,
      attendance_state,
      create_uid,
      write_uid,
      create_date,
      write_date
    )
    VALUES (
      session_id_val,
      member_id_val,
      'registered',
      'pending',
      1,
      1,
      NOW(),
      NOW()
    )
    ON CONFLICT DO NOTHING;
  END IF;
END $$;

-- Set up admin user for gate tests
-- Update admin login to admin@demo.com and password to admin123
UPDATE res_users
SET login = 'admin@demo.com',
    password = '$pbkdf2-sha512$25000$PceY8763tpbS.h8jZEzJOQ$9R75uT4b1i/dHt3DHtRlG1Nh4JjsKbpoxCgu7a0DHQaoXU6qTihS8.9gXuH0hOYUsA2nEao5FjIfJV2gnDlOAg'
WHERE id = 2;

-- Add admin to instructor group (required for /odoo/export/students endpoint)
DO $$
DECLARE
  instructor_group_id integer;
BEGIN
  SELECT id INTO instructor_group_id FROM res_groups WHERE name::text LIKE '%Dojo Instructor%' LIMIT 1;

  IF instructor_group_id IS NOT NULL THEN
    INSERT INTO res_groups_users_rel (gid, uid)
    VALUES (instructor_group_id, 2)
    ON CONFLICT DO NOTHING;
  END IF;
END $$;
