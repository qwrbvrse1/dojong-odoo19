-- Migration: dojo_assistant → ai_assistant
-- Also moves intent ir_model_data ownership from ai_assistant → ai_vector
-- Run BEFORE upgrading modules
BEGIN;
-- ═══════════════════════════════════════════════════════════
-- 1. Rename module in ir_module_module
-- ═══════════════════════════════════════════════════════════
UPDATE ir_module_module
SET name = 'ai_assistant'
WHERE name = 'dojo_assistant';
-- ═══════════════════════════════════════════════════════════
-- 2. Rename database tables
-- ═══════════════════════════════════════════════════════════
ALTER TABLE IF EXISTS dojo_ai_intent_schema
    RENAME TO ai_intent_schema;
ALTER TABLE IF EXISTS dojo_ai_action_log
    RENAME TO ai_action_log;
ALTER TABLE IF EXISTS dojo_ai_undo_snapshot
    RENAME TO ai_undo_snapshot;
ALTER TABLE IF EXISTS dojo_walkie_talkie
    RENAME TO ai_walkie_talkie;
ALTER TABLE IF EXISTS dojo_walkie_channel_mapping
    RENAME TO ai_walkie_channel_mapping;
-- Rename M2M relation tables if they exist
ALTER TABLE IF EXISTS ai_agent_dojo_ai_intent_schema_rel
    RENAME TO ai_agent_ai_intent_schema_rel;
-- ═══════════════════════════════════════════════════════════
-- 3. Update ir_model (model registry)
-- ═══════════════════════════════════════════════════════════
UPDATE ir_model
SET model = 'ai.intent.schema'
WHERE model = 'dojo.ai.intent.schema';
UPDATE ir_model
SET model = 'ai.action.log'
WHERE model = 'dojo.ai.action.log';
UPDATE ir_model
SET model = 'ai.undo.snapshot'
WHERE model = 'dojo.ai.undo.snapshot';
UPDATE ir_model
SET model = 'ai.walkie.talkie'
WHERE model = 'dojo.walkie.talkie';
UPDATE ir_model
SET model = 'ai.walkie.channel.mapping'
WHERE model = 'dojo.walkie.channel.mapping';
-- ═══════════════════════════════════════════════════════════
-- 4. Update ir_model_fields
-- ═══════════════════════════════════════════════════════════
UPDATE ir_model_fields
SET model = 'ai.intent.schema'
WHERE model = 'dojo.ai.intent.schema';
UPDATE ir_model_fields
SET model = 'ai.action.log'
WHERE model = 'dojo.ai.action.log';
UPDATE ir_model_fields
SET model = 'ai.undo.snapshot'
WHERE model = 'dojo.ai.undo.snapshot';
UPDATE ir_model_fields
SET model = 'ai.walkie.talkie'
WHERE model = 'dojo.walkie.talkie';
UPDATE ir_model_fields
SET model = 'ai.walkie.channel.mapping'
WHERE model = 'dojo.walkie.channel.mapping';
-- Also update relation fields pointing TO these models
UPDATE ir_model_fields
SET relation = 'ai.intent.schema'
WHERE relation = 'dojo.ai.intent.schema';
UPDATE ir_model_fields
SET relation = 'ai.action.log'
WHERE relation = 'dojo.ai.action.log';
UPDATE ir_model_fields
SET relation = 'ai.undo.snapshot'
WHERE relation = 'dojo.ai.undo.snapshot';
UPDATE ir_model_fields
SET relation = 'ai.walkie.talkie'
WHERE relation = 'dojo.walkie.talkie';
UPDATE ir_model_fields
SET relation = 'ai.walkie.channel.mapping'
WHERE relation = 'dojo.walkie.channel.mapping';
-- ═══════════════════════════════════════════════════════════
-- 5. Update ir_model_data (XML ID ownership)
-- ═══════════════════════════════════════════════════════════
-- General: all dojo_assistant records → ai_assistant
UPDATE ir_model_data
SET module = 'ai_assistant'
WHERE module = 'dojo_assistant';
-- Move intent records to ai_vector (they now live in ai_vector/data/)
UPDATE ir_model_data
SET module = 'ai_vector'
WHERE module = 'ai_assistant'
    AND name LIKE 'intent_%';
-- Update model references in ir_model_data
UPDATE ir_model_data
SET model = 'ai.intent.schema'
WHERE model = 'dojo.ai.intent.schema';
UPDATE ir_model_data
SET model = 'ai.action.log'
WHERE model = 'dojo.ai.action.log';
UPDATE ir_model_data
SET model = 'ai.undo.snapshot'
WHERE model = 'dojo.ai.undo.snapshot';
UPDATE ir_model_data
SET model = 'ai.walkie.talkie'
WHERE model = 'dojo.walkie.talkie';
UPDATE ir_model_data
SET model = 'ai.walkie.channel.mapping'
WHERE model = 'dojo.walkie.channel.mapping';
-- ═══════════════════════════════════════════════════════════
-- 6. Update ir_model_access
-- ═══════════════════════════════════════════════════════════
UPDATE ir_model_access
SET name = REPLACE(
        name,
        'dojo.ai.intent.schema',
        'ai.intent.schema'
    )
WHERE name LIKE '%dojo.ai.intent.schema%';
UPDATE ir_model_access
SET name = REPLACE(name, 'dojo.ai.action.log', 'ai.action.log')
WHERE name LIKE '%dojo.ai.action.log%';
UPDATE ir_model_access
SET name = REPLACE(
        name,
        'dojo.ai.undo.snapshot',
        'ai.undo.snapshot'
    )
WHERE name LIKE '%dojo.ai.undo.snapshot%';
-- ═══════════════════════════════════════════════════════════
-- 7. Update ir_config_parameter
-- ═══════════════════════════════════════════════════════════
UPDATE ir_config_parameter
SET key = REPLACE(key, 'dojo_assistant.', 'ai_assistant.')
WHERE key LIKE 'dojo_assistant.%';
-- ═══════════════════════════════════════════════════════════
-- 8. Update ir_model_constraint
-- ═══════════════════════════════════════════════════════════
UPDATE ir_model_constraint
SET module = (
        SELECT id
        FROM ir_module_module
        WHERE name = 'ai_assistant'
    )
WHERE module IN (
        SELECT id
        FROM ir_module_module
        WHERE name = 'dojo_assistant'
    );
-- ═══════════════════════════════════════════════════════════
-- 9. Rename sequences if any exist
-- ═══════════════════════════════════════════════════════════
ALTER SEQUENCE IF EXISTS dojo_ai_intent_schema_id_seq
RENAME TO ai_intent_schema_id_seq;
ALTER SEQUENCE IF EXISTS dojo_ai_action_log_id_seq
RENAME TO ai_action_log_id_seq;
ALTER SEQUENCE IF EXISTS dojo_ai_undo_snapshot_id_seq
RENAME TO ai_undo_snapshot_id_seq;
ALTER SEQUENCE IF EXISTS dojo_walkie_talkie_id_seq
RENAME TO ai_walkie_talkie_id_seq;
ALTER SEQUENCE IF EXISTS dojo_walkie_channel_mapping_id_seq
RENAME TO ai_walkie_channel_mapping_id_seq;
COMMIT;