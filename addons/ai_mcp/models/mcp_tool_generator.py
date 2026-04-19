# -*- coding: utf-8 -*-
"""
MCP Tool Generator — auto-generates MCP tool definitions from intent schemas.

Each ``ai.intent.schema`` record becomes an MCP tool with:
  - name:        intent_type
  - description: schema description + examples
  - inputSchema: JSON Schema from parameters_schema
"""

import json
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AiMcpToolGenerator(models.AbstractModel):
    _name = "ai.mcp.tool.generator"
    _description = "MCP Tool Generator"

    @api.model
    def generate_tool_list(self, role="instructor"):
        """
        Generate MCP tool definitions from all active intent schemas.

        Args:
            role: Caller role — filters to only role-permitted intents.

        Returns:
            list[dict]: MCP-compliant tool definitions.
        """
        schemas = (
            self.env["ai.intent.schema"]
            .sudo()
            .search([("active", "=", True)], order="sequence, intent_type")
        )

        tools = []
        for schema in schemas:
            if not schema.check_role_permission(role):
                continue

            tool = self._schema_to_tool(schema)
            if tool:
                tools.append(tool)

        _logger.info(
            "MCP: generated %d tools for role '%s' (from %d schemas)",
            len(tools),
            role,
            len(schemas),
        )
        return tools

    @api.model
    def _schema_to_tool(self, schema):
        """
        Convert a single intent schema record to an MCP tool definition.

        Args:
            schema: ``ai.intent.schema`` record

        Returns:
            dict: MCP tool definition or None if invalid.
        """
        # Build description with examples
        desc_parts = []
        if schema.description:
            desc_parts.append(schema.description.strip())

        examples = schema.get_example_phrases_list()
        if examples:
            desc_parts.append("Examples: " + "; ".join(examples[:5]))

        if schema.requires_confirmation:
            desc_parts.append("[Requires confirmation before execution]")

        description = "\n".join(desc_parts) if desc_parts else schema.name

        # Build input schema from parameters_schema
        input_schema = self._build_input_schema(schema)

        return {
            "name": schema.intent_type,
            "description": description,
            "inputSchema": input_schema,
        }

    @api.model
    def _build_input_schema(self, schema):
        """
        Build a JSON Schema ``inputSchema`` for the MCP tool.

        Converts the intent's ``parameters_schema`` into a proper
        JSON Schema object with type annotations.
        """
        params = schema.get_parameters_schema_dict()

        if not params:
            return {"type": "object", "properties": {}}

        # If the schema is already a well-formed JSON Schema, use it
        if "type" in params and "properties" in params:
            return params

        # Convert flat param dict to JSON Schema
        properties = {}
        required = []

        for key, value in params.items():
            if isinstance(value, str):
                # Simple format: {"member_name": "Name of the member"}
                properties[key] = {
                    "type": "string",
                    "description": value,
                }
            elif isinstance(value, dict):
                # Rich format: {"member_name": {"type": "string", "description": "...", "required": true}}
                prop = {
                    "type": value.get("type", "string"),
                    "description": value.get("description", key),
                }
                if value.get("enum"):
                    prop["enum"] = value["enum"]
                if value.get("default") is not None:
                    prop["default"] = value["default"]
                properties[key] = prop

                if value.get("required"):
                    required.append(key)

        result = {
            "type": "object",
            "properties": properties,
        }
        if required:
            result["required"] = required

        return result
