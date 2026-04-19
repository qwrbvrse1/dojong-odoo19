# -*- coding: utf-8 -*-
"""
Agent definitions — one file per domain agent.

Each file exports an AGENT_CONFIG dict used by ai_agent_data.xml
to seed agent records. This makes it immediately obvious which
agents exist by browsing the file tree.
"""

from .core_agent import AGENT_CONFIG as CORE
from .attendance_agent import AGENT_CONFIG as ATTENDANCE
from .enrollment_agent import AGENT_CONFIG as ENROLLMENT
from .subscriptions_agent import AGENT_CONFIG as SUBSCRIPTIONS
from .crm_agent import AGENT_CONFIG as CRM
from .communications_agent import AGENT_CONFIG as COMMUNICATIONS
from .marketing_agent import AGENT_CONFIG as MARKETING
from .belt_rank_agent import AGENT_CONFIG as BELT_RANK
from .calendar_agent import AGENT_CONFIG as CALENDAR

ALL_AGENTS = [
    CORE,
    ATTENDANCE,
    ENROLLMENT,
    SUBSCRIPTIONS,
    CRM,
    COMMUNICATIONS,
    MARKETING,
    BELT_RANK,
    CALENDAR,
]
