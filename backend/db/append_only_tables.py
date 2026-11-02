"""Canonical lims_app privilege revokes that must survive ensure_lims_app_role.

``ensure_lims_app_role.py`` grants SELECT, INSERT, UPDATE, DELETE on every
public table, then re-applies this map. Keep it in lockstep with every
migration that REVOKEs INSERT, UPDATE, or DELETE from lims_app.

Values are the privileges to REVOKE. Tables that only lost DELETE still
accept UPDATE (soft-retire). Append-only / immutable tables lose UPDATE
and DELETE.
"""
from __future__ import annotations

from typing import FrozenSet, Mapping

# table -> privileges to revoke from lims_app after the blanket GRANT.
APPEND_ONLY_REVOKES: Mapping[str, FrozenSet[str]] = {
    # 0095 / 0118 — CREATE granted SELECT/INSERT/UPDATE only; ensure must
    # not put DELETE back.
    "lab_settings": frozenset({"DELETE"}),
    # 0108
    "result_acceptances": frozenset({"DELETE"}),
    # 0109
    "vendors": frozenset({"DELETE"}),
    "reagents": frozenset({"DELETE"}),
    "reagent_vendors": frozenset({"DELETE"}),
    "reagent_lots": frozenset({"DELETE"}),
    "reagent_uses": frozenset({"DELETE"}),
    # 0111
    "instruments": frozenset({"DELETE"}),
    "cro_sources": frozenset({"DELETE"}),
    "instrument_maintenance_schedules": frozenset({"DELETE"}),
    "instrument_maintenance_events": frozenset({"DELETE"}),
    "instrument_downtime": frozenset({"DELETE"}),
    "instrument_uses": frozenset({"DELETE"}),
    # 0112
    "instrument_types_legacy": frozenset({"INSERT", "UPDATE", "DELETE"}),
    # 0113 / 0114
    "instrument_type_defaults": frozenset({"INSERT", "UPDATE", "DELETE"}),
    "instrument_maintenance_audits": frozenset({"UPDATE", "DELETE"}),
    "instrument_schedule_audits": frozenset({"UPDATE", "DELETE"}),
    # 0115
    "lims_run_type_substitutions": frozenset({"UPDATE", "DELETE"}),
    # 0116
    "instrument_template_inactivations": frozenset({"UPDATE", "DELETE"}),
    # 0117
    "instrument_entry_slot_audits": frozenset({"UPDATE", "DELETE"}),
    "lims_run_imports": frozenset({"UPDATE", "DELETE"}),
    "lims_run_data": frozenset({"UPDATE", "DELETE"}),
    # 0119
    "instrument_type_deactivations": frozenset({"UPDATE", "DELETE"}),
}

# Login roles that may skip app-row guards. session_user is not changed by
# SECURITY DEFINER. Superuser testcontainer logins are detected separately.
MAINTENANCE_SESSION_ROLES = ("lims_migrate", "schema_apply", "postgres")
