"""Convert naive UTC instant columns to timestamptz.

Revision ID: 0102_instant_timestamptz
Revises: 0101_revoke_probe_execute

Each converted column is ``timestamp without time zone`` holding a UTC wall
time. ``USING col AT TIME ZONE 'UTC'`` reads that wall time as UTC, so the
instant does not shift. Downgrade writes the UTC wall time back with the same
expression.

Calendar-day columns are already SQL ``date`` from ``0100_calendar_dates``.
Reagent SQL ``date`` columns are not altered. Custom-attribute JSON is not a
timestamp column and is not rewritten.

The column lists below are frozen in this revision. They are not imported
from application models, so a later model edit cannot change what this
migration alters.

Views, materialized views, rules, and generated columns that depend on a
converted column stop the migration. Indexes, defaults, triggers, and row
level security policies are left in place; Postgres rebuilds a plain index
when the column type changes.
"""

from __future__ import annotations

import re

from alembic import op
from sqlalchemy import text

# No lab day remains ``timestamp without time zone`` when this revision runs.
CALENDAR_TIMESTAMP_COLUMNS = frozenset([])

# Civil dates. Already SQL date. This revision does not alter them.
SQL_DATE_COLUMNS = frozenset(
    [
        "batches.start_date",
        "batches.end_date",
        "projects.start_date",
        "projects.due_date",
        "samples.due_date",
        "samples.received_date",
        "samples.report_date",
        "samples.date_sampled",
        "tests.review_date",
        "tests.test_date",
        "results.entry_date",
        "reagent_lots.expiration_date",
        "reagent_lots.purchased_date",
        "reagent_lots.received_date",
        "reagent_lots.opened_date",
        "reagent_uses.expiration_date",
        "reagent_uses.used_on",
    ]
)

# Naive timestamp columns converted to timestamptz. Frozen at this revision.
INSTANT_TIMESTAMP_COLUMNS = frozenset(
    [
        "analyses.created_at",
        "analyses.modified_at",
        "analysis_param_defs.created_at",
        "analysis_param_defs.modified_at",
        "analyte_aliases.created_at",
        "analytes.created_at",
        "analytes.modified_at",
        "asked_for.created_at",
        "asked_for.modified_at",
        "batches.created_at",
        "batches.modified_at",
        "client_projects.created_at",
        "client_projects.modified_at",
        "clients.created_at",
        "clients.modified_at",
        "container_types.created_at",
        "container_types.modified_at",
        "containers.created_at",
        "containers.modified_at",
        "cro_sources.created_at",
        "cro_sources.modified_at",
        "custom_attributes_config.created_at",
        "custom_attributes_config.modified_at",
        "data_parsers.created_at",
        "data_parsers.modified_at",
        "eln_process_definition_steps.created_at",
        "eln_process_definition_steps.modified_at",
        "eln_process_definitions.created_at",
        "eln_process_definitions.modified_at",
        "eln_process_samples.created_at",
        "eln_process_samples.modified_at",
        "eln_process_step_lims_runs.created_at",
        "eln_process_steps.created_at",
        "eln_process_steps.modified_at",
        "eln_processes.created_at",
        "eln_processes.modified_at",
        "entries.created_at",
        "entries.modified_at",
        "entry_field_values.created_at",
        "entry_field_values.modified_at",
        "experiment_details.created_at",
        "experiment_details.modified_at",
        "experiment_sample_executions.created_at",
        "experiment_sample_executions.modified_at",
        "experiment_templates.created_at",
        "experiment_templates.modified_at",
        "experiments.started_at",
        "experiments.completed_at",
        "experiments.created_at",
        "experiments.modified_at",
        "field_definitions.created_at",
        "field_definitions.modified_at",
        "help_entries.created_at",
        "help_entries.modified_at",
        "instrument_types.created_at",
        "instrument_types.modified_at",
        "instruments.created_at",
        "instruments.modified_at",
        "lims_run_checklist_steps.started_at",
        "lims_run_checklist_steps.completed_at",
        "lims_run_checklist_steps.failed_at",
        "lims_run_checklist_steps.created_at",
        "lims_run_checklist_steps.modified_at",
        "lims_run_checklists.created_at",
        "lims_run_checklists.modified_at",
        "lims_run_data.created_at",
        "lims_run_data.modified_at",
        "lims_run_imports.imported_at",
        "lims_runs.started_at",
        "lims_runs.completed_at",
        "lims_runs.published_at",
        "lims_runs.canceled_at",
        "lims_runs.created_at",
        "lims_runs.modified_at",
        "list_entries.created_at",
        "list_entries.modified_at",
        "lists.created_at",
        "lists.modified_at",
        "locations.created_at",
        "locations.modified_at",
        "name_templates.created_at",
        "name_templates.modified_at",
        "parser_setup_files.created_at",
        "people.created_at",
        "people.modified_at",
        "permissions.created_at",
        "permissions.modified_at",
        "project_users.granted_at",
        "projects.created_at",
        "projects.modified_at",
        "reagent_lots.created_at",
        "reagent_lots.modified_at",
        "reagent_uses.created_at",
        "reagent_uses.modified_at",
        "reagent_vendors.created_at",
        "reagent_vendors.modified_at",
        "reagents.created_at",
        "reagents.modified_at",
        "results.created_at",
        "results.modified_at",
        "robot_worklist_configs.created_at",
        "robot_worklist_configs.modified_at",
        "roles.created_at",
        "roles.modified_at",
        "routing_map.created_at",
        "routing_map.modified_at",
        "sample_type_transitions.created_at",
        "sample_type_transitions.modified_at",
        "samples.created_at",
        "samples.modified_at",
        "schema_changes.created_at",
        "schema_columns.created_at",
        "schema_columns.modified_at",
        "schema_layouts.created_at",
        "schema_layouts.modified_at",
        "schema_privileges.created_at",
        "schema_privileges.modified_at",
        "schema_relations.created_at",
        "schema_relations.modified_at",
        "schema_tables.created_at",
        "schema_tables.modified_at",
        "sop_parse_jobs.created_at",
        "sop_parse_jobs.modified_at",
        "test_batteries.created_at",
        "test_batteries.modified_at",
        "tests.created_at",
        "tests.modified_at",
        "ui_schema_ddl_log.applied_at",
        "units.created_at",
        "units.modified_at",
        "users.last_login",
        "users.created_at",
        "users.modified_at",
        "vendors.created_at",
        "vendors.modified_at",
        "work_orders.created_at",
        "work_orders.modified_at",
        "workflow_instances.created_at",
        "workflow_instances.modified_at",
        "workflow_templates.created_at",
        "workflow_templates.modified_at",
    ]
)

revision = "0102_instant_timestamptz"
down_revision = "0101_revoke_probe_execute"
branch_labels = None
depends_on = None

_NAIVE = "timestamp without time zone"
_AWARE = "timestamp with time zone"
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def upgrade() -> None:
    conn = op.get_bind()
    _require_expected_types(conn, source=_NAIVE)
    _refuse_unsafe_dependents(conn)
    for qualified in sorted(INSTANT_TIMESTAMP_COLUMNS):
        _alter_instant(conn, qualified, _AWARE)


def downgrade() -> None:
    conn = op.get_bind()
    _require_expected_types(conn, source=_AWARE)
    _refuse_unsafe_dependents(conn)
    for qualified in sorted(INSTANT_TIMESTAMP_COLUMNS):
        _alter_instant(conn, qualified, _NAIVE)


def _require_expected_types(conn, source: str) -> None:
    """Fail before any ALTER when the catalog does not match this revision."""
    naive = _columns_of_type(conn, _NAIVE)
    aware = _columns_of_type(conn, _AWARE)
    dates = _columns_of_type(conn, "date")
    present = naive if source == _NAIVE else aware
    missing = sorted(INSTANT_TIMESTAMP_COLUMNS - present)
    unexpected = sorted(naive - CALENDAR_TIMESTAMP_COLUMNS - INSTANT_TIMESTAMP_COLUMNS)
    calendar_moved = sorted(CALENDAR_TIMESTAMP_COLUMNS - naive)
    dates_moved = sorted(SQL_DATE_COLUMNS - dates)
    problems: list[str] = []
    if missing:
        problems.append(
            "instant columns not "
            + source
            + ": "
            + ", ".join(missing)
        )
    if unexpected:
        problems.append(
            "unexpected timestamp without time zone: " + ", ".join(unexpected)
        )
    if calendar_moved:
        problems.append(
            "calendar columns are not timestamp without time zone: "
            + ", ".join(calendar_moved)
        )
    if dates_moved:
        problems.append("SQL date columns changed: " + ", ".join(dates_moved))
    if problems:
        raise RuntimeError(
            "0102_instant_timestamptz refused to change types. "
            + " ".join(problems)
        )


def _columns_of_type(conn, data_type: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema = c.table_schema
             AND t.table_name = c.table_name
            WHERE c.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
              AND c.data_type = :data_type
            """
        ),
        {"data_type": data_type},
    )
    return {f"{table}.{column}" for table, column in rows}


def _refuse_unsafe_dependents(conn) -> None:
    """Stop when a converted column cannot change type without a drop."""
    tables = {name.split(".", 1)[0] for name in INSTANT_TIMESTAMP_COLUMNS}
    blockers: list[str] = []
    view_rows = conn.execute(
        text(
            """
            SELECT source.relname AS table_name,
                   a.attname AS column_name,
                   dependent_ns.nspname AS dep_schema,
                   dependent.relname AS dep_name,
                   dependent.relkind AS dep_kind
            FROM pg_depend d
            JOIN pg_rewrite rw ON d.objid = rw.oid
            JOIN pg_class dependent ON rw.ev_class = dependent.oid
            JOIN pg_namespace dependent_ns ON dependent_ns.oid = dependent.relnamespace
            JOIN pg_class source ON d.refobjid = source.oid
            JOIN pg_namespace source_ns ON source_ns.oid = source.relnamespace
            JOIN pg_attribute a
              ON a.attrelid = source.oid
             AND a.attnum = d.refobjsubid
             AND a.attnum > 0
            WHERE source_ns.nspname = 'public'
              AND dependent.oid <> source.oid
              AND dependent.relkind IN ('v', 'm')
            """
        )
    )
    for table_name, column_name, dep_schema, dep_name, dep_kind in view_rows:
        if table_name not in tables:
            continue
        qualified = f"{table_name}.{column_name}"
        if qualified not in INSTANT_TIMESTAMP_COLUMNS:
            continue
        kind = "materialized view" if dep_kind == "m" else "view"
        blockers.append(
            f"{qualified} is used by {kind} {dep_schema}.{dep_name}"
        )

    rule_rows = conn.execute(
        text(
            """
            SELECT c.relname, r.rulename
            FROM pg_rewrite r
            JOIN pg_class c ON c.oid = r.ev_class
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND r.rulename <> '_RETURN'
            """
        )
    )
    for table_name, rule_name in rule_rows:
        if table_name not in tables:
            continue
        blockers.append(f"{table_name} has rule {rule_name}")

    generated_rows = conn.execute(
        text(
            """
            SELECT c.relname, a.attname
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND a.attgenerated <> ''
              AND NOT a.attisdropped
            """
        )
    )
    for table_name, column_name in generated_rows:
        if table_name not in tables:
            continue
        qualified = f"{table_name}.{column_name}"
        if qualified in INSTANT_TIMESTAMP_COLUMNS:
            blockers.append(f"{qualified} is a generated column")

    if blockers:
        raise RuntimeError(
            "0102_instant_timestamptz stopped. A dependent object would have "
            "to be dropped, and this migration does not drop schema objects: "
            + "; ".join(sorted(blockers))
        )


def _alter_instant(conn, qualified: str, target: str) -> None:
    table, column = qualified.split(".", 1)
    _ident(table)
    _ident(column)
    if target not in (_NAIVE, _AWARE):
        raise RuntimeError(f"unexpected target type {target}")
    conn.execute(
        text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target} "
            f"USING {column} AT TIME ZONE 'UTC'"
        )
    )


def _ident(name: str) -> None:
    if _IDENT.fullmatch(name) is None:
        raise RuntimeError(f"unexpected identifier {name}")
