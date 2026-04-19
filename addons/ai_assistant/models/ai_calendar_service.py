# -*- coding: utf-8 -*-
"""
AI Calendar Service — Extends ai.assistant.service with calendar.event intents.

Handlers:
- calendar_event_list  (read-only, auto-execute)
- calendar_event_create  (requires confirmation)
- calendar_event_cancel  (admin-only, requires confirmation)
"""
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiCalendarService(models.AbstractModel):
    _inherit = "ai.assistant.service"

    # ═══════════════════════════════════════════════════════════════════════════
    # Domain Builder — Calendar Event List
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model
    def _domain_calendar_event_list(self, intent_data, resolved_data):
        """Build domain for listing calendar events.

        Parameters from intent:
          - date_filter: 'today' | 'tomorrow' | 'this_week' | 'next_week' (default: 'today')
          - event_name: partial name filter (optional)
        """
        params = intent_data.get("parameters", {}) if intent_data else {}
        today = fields.Date.today()
        date_filter = params.get("date_filter", "today")

        if date_filter == "today":
            start = datetime.combine(today, datetime.min.time())
            end = datetime.combine(today, datetime.max.time())
        elif date_filter == "tomorrow":
            tomorrow = today + timedelta(days=1)
            start = datetime.combine(tomorrow, datetime.min.time())
            end = datetime.combine(tomorrow, datetime.max.time())
        elif date_filter == "this_week":
            # Monday of current week → Sunday
            day_of_week = today.weekday()
            monday = today - timedelta(days=day_of_week)
            sunday = monday + timedelta(days=6)
            start = datetime.combine(monday, datetime.min.time())
            end = datetime.combine(sunday, datetime.max.time())
        elif date_filter == "next_week":
            day_of_week = today.weekday()
            next_monday = today + timedelta(days=(7 - day_of_week))
            next_sunday = next_monday + timedelta(days=6)
            start = datetime.combine(next_monday, datetime.min.time())
            end = datetime.combine(next_sunday, datetime.max.time())
        else:
            # Fallback: 7 days from today
            start = datetime.combine(today, datetime.min.time())
            end = datetime.combine(today + timedelta(days=7), datetime.max.time())

        domain = [
            ("start", ">=", start.strftime("%Y-%m-%d %H:%M:%S")),
            ("start", "<=", end.strftime("%Y-%m-%d %H:%M:%S")),
        ]

        event_name = params.get("event_name") or params.get("name")
        if event_name:
            domain.append(("name", "ilike", event_name))

        return domain

    # ═══════════════════════════════════════════════════════════════════════════
    # Handler: calendar_event_list (generic read, domain builder used automatically)
    # ═══════════════════════════════════════════════════════════════════════════
    # Note: calendar_event_list is handled by _handle_generic_read using
    # _domain_calendar_event_list. We only need custom handlers for create/cancel.

    # ═══════════════════════════════════════════════════════════════════════════
    # Handler: calendar_event_create
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model
    def _handle_calendar_event_create(self, intent_data, resolved_data, action_log):
        """Create a calendar event.

        Parameters:
          - name (required): event title
          - start: start datetime string (YYYY-MM-DD HH:MM or YYYY-MM-DD)
          - stop / duration_minutes: end or duration
          - description: optional description
          - location: optional location
        """
        params = intent_data.get("parameters", {}) if intent_data else {}
        name = params.get("name") or params.get("event_name") or params.get("title")
        if not name:
            return {"success": False, "error": "Please provide a name for the calendar event."}

        # Parse start datetime
        start_str = params.get("start") or params.get("start_datetime") or params.get("date")
        if not start_str:
            return {"success": False, "error": "Please provide a start date/time for the event."}

        try:
            start_dt = self._parse_datetime(start_str)
        except Exception:
            return {"success": False, "error": f"Could not parse start date/time: '{start_str}'."}

        # Parse stop datetime
        stop_str = params.get("stop") or params.get("end") or params.get("stop_datetime")
        if stop_str:
            try:
                stop_dt = self._parse_datetime(stop_str)
            except Exception:
                stop_dt = start_dt + timedelta(hours=1)
        else:
            duration_minutes = int(params.get("duration_minutes", 60))
            stop_dt = start_dt + timedelta(minutes=duration_minutes)

        values = {
            "name": name,
            "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "stop": stop_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "description": params.get("description", ""),
            "location": params.get("location", ""),
            "user_id": self.env.uid,
        }

        try:
            event = self.env["calendar.event"].create(values)

            # Snapshot for undo
            Snapshot = self.env["ai.undo.snapshot"]
            Snapshot.create_snapshot(action_log.id, "calendar.event", event.id, "create")

            return {
                "success": True,
                "message": f"Calendar event '{name}' created on {start_dt.strftime('%A, %B %d at %I:%M %p')}.",
                "data": {
                    "event_id": event.id,
                    "name": name,
                    "start": values["start"],
                    "stop": values["stop"],
                },
            }
        except Exception as exc:
            _logger.error("AI calendar_event_create failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    # ═══════════════════════════════════════════════════════════════════════════
    # Handler: calendar_event_cancel (admin-only)
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model
    def _handle_calendar_event_cancel(self, intent_data, resolved_data, action_log):
        """Cancel (delete) a calendar event.

        Parameters:
          - event_name: name or partial name of the event
          - event_id: ID of the event (preferred)
          - start: start date/time to disambiguate when multiple events match
        """
        params = intent_data.get("parameters", {}) if intent_data else {}
        event_id = params.get("event_id") or resolved_data.get("event_id")
        event_name = params.get("event_name") or params.get("name")

        Event = self.env["calendar.event"]

        if event_id:
            event = Event.browse(int(event_id))
        elif event_name:
            # Try to match by name + optional date disambiguator
            start_str = params.get("start") or params.get("date")
            domain = [("name", "ilike", event_name)]
            if start_str:
                try:
                    start_dt = self._parse_datetime(start_str)
                    domain += [
                        ("start", ">=", start_dt.strftime("%Y-%m-%d 00:00:00")),
                        ("start", "<=", start_dt.strftime("%Y-%m-%d 23:59:59")),
                    ]
                except Exception:
                    pass
            event = Event.search(domain, limit=1)
        else:
            return {"success": False, "error": "Please specify the event name or ID to cancel."}

        if not event or not event.exists():
            return {"success": False, "error": f"Calendar event '{event_name}' not found."}

        event_display = f"'{event.name}' on {event.start}"

        # Snapshot for undo
        Snapshot = self.env["ai.undo.snapshot"]
        Snapshot.create_snapshot(action_log.id, "calendar.event", event.id, "unlink",
                                  snapshot_data=event.read()[0])

        try:
            event.unlink()
            return {
                "success": True,
                "message": f"Calendar event {event_display} has been cancelled.",
                "data": {},
            }
        except Exception as exc:
            _logger.error("AI calendar_event_cancel failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    # ═══════════════════════════════════════════════════════════════════════════
    # Utility: datetime parser
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model
    def _parse_datetime(self, value):
        """Parse a datetime string in multiple common formats."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(str(value).strip(), fmt)
                # If date-only, default to 08:00
                if fmt in ("%Y-%m-%d", "%m/%d/%Y"):
                    dt = dt.replace(hour=8, minute=0)
                return dt
            except ValueError:
                continue
        raise ValueError(f"Cannot parse datetime: {value}")
