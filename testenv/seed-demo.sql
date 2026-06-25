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
