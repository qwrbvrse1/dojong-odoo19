# -*- coding: utf-8 -*-
"""
AI Agent — Domain-specific agent definitions for multi-agent orchestration.

Each agent owns a subset of intents and carries a focused system prompt
template. The vector router uses the agent's domain to group intents
and route queries to the right expert.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Agent domain definitions — used by vector store for tagging
AGENT_DOMAINS = [
    ("core", "Core"),
    ("attendance", "Attendance"),
    ("enrollment", "Enrollment"),
    ("subscriptions", "Subscriptions"),
    ("crm", "CRM / Pipeline"),
    ("communications", "Communications"),
    ("marketing", "Marketing"),
    ("belt_rank", "Belt / Rank"),
    ("calendar", "Calendar / Scheduling"),
]


class AiAgent(models.Model):
    _name = "ai.agent"
    _description = "AI Domain Agent"
    _order = "sequence, name"
    _rec_name = "name"

    name = fields.Char(
        string="Name",
        required=True,
    )
    domain = fields.Selection(
        selection=AGENT_DOMAINS,
        string="Domain",
        required=True,
        index=True,
    )
    description = fields.Text(
        string="Description",
        help="What this agent specialises in",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    intent_ids = fields.Many2many(
        "ai.intent.schema",
        "ai_agent_intent_rel",
        "agent_id",
        "intent_id",
        string="Intents",
        help="Intent schemas handled by this agent",
    )
    system_prompt_template = fields.Text(
        string="System Prompt Template",
        help="LLM system prompt template for this agent. "
             "Use {intent_definitions} and {db_context} placeholders.",
    )
    intent_count = fields.Integer(
        string="# Intents",
        compute="_compute_intent_count",
        store=False,
    )
    color = fields.Integer(string="Color Index")

    _sql_constraints = [
        (
            "domain_unique",
            "UNIQUE(domain)",
            "Each domain can only have one agent.",
        ),
    ]

    @api.depends("intent_ids")
    def _compute_intent_count(self):
        for rec in self:
            rec.intent_count = len(rec.intent_ids)

    @api.model
    def get_agent_for_intent(self, intent_type):
        """Find the agent responsible for a given intent type."""
        agent = self.search([
            ("intent_ids.intent_type", "=", intent_type),
            ("active", "=", True),
        ], limit=1)
        return agent

    @api.model
    def get_agent_for_domain(self, domain):
        """Find the agent for a given domain."""
        return self.search([
            ("domain", "=", domain),
            ("active", "=", True),
        ], limit=1)

    def get_intent_definitions_for_llm(self, role=None):
        """
        Get intent definitions scoped to this agent, formatted for LLM prompt.

        This returns only this agent's intents — not all 57.
        """
        self.ensure_one()
        intents = self.intent_ids.filtered(lambda i: i.active)
        if role:
            intents = intents.filtered(lambda i: i.check_role_permission(role))

        definitions = []
        for intent in intents:
            definitions.append({
                "intent_type": intent.intent_type,
                "name": intent.name,
                "description": intent.description or "",
                "parameters": intent.get_parameters_schema_dict(),
                "examples": intent.get_example_phrases_list(),
                "requires_confirmation": intent.requires_confirmation,
            })
        return definitions

    def execute(self, intent_type, resolved_data, role="instructor"):
        """
        Agent execution hook — delegates to ai.assistant.service.

        Routes through the standard 3-tier handler dispatch.

        Args:
            intent_type: The parsed intent type string.
            resolved_data: Resolved parameter dict from the LLM.
            role: User role for permission checks.

        Returns:
            dict: Execution result from the intent handler.
        """
        self.ensure_one()
        _logger.info(
            "Agent '%s' (domain=%s) executing intent '%s'",
            self.name,
            self.domain,
            intent_type,
        )
        service = self.env["ai.assistant.service"]
        return service._execute_intent(
            intent_type,
            {},              # intent_data — raw LLM output not available in direct mode
            resolved_data,
            None,            # action_log — no pending session for direct calls
        )
