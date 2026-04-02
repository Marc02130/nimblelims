"""
One-time data migration: extract plate_layout well data from template_definition JSONB
into the new template_well_definitions table.

Run AFTER migration 0043 has been applied:
    docker exec lims-backend python db/migrations/data/migrate_plate_layout_to_wells.py

This script is idempotent: re-running it will skip templates that already have
template_well_definitions rows (based on the unique constraint).

Does NOT delete data from template_definition JSONB — the JSONB remains as a
visual/structural reference. template_well_definitions is now authoritative for
analytical data (concentrations, replicate_group).
"""
import sys
import os
import uuid

# Ensure the backend root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://lims_user:lims_password@localhost:5432/lims_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def migrate() -> None:
    db = SessionLocal()
    try:
        # Load all templates with a plate_layout in their template_definition
        templates = db.execute(
            text("""
                SELECT id, client_id, template_definition
                FROM experiment_templates
                WHERE template_definition -> 'plate_layout' -> 'wells' IS NOT NULL
            """)
        ).fetchall()

        print(f"Found {len(templates)} templates with plate_layout.wells to migrate.")
        migrated = 0
        skipped = 0

        for tmpl in templates:
            tmpl_id = tmpl[0]
            client_id = tmpl[1]
            template_def = tmpl[2] or {}

            plate_layout = template_def.get("plate_layout", {})
            wells = plate_layout.get("wells", {})

            if not wells:
                skipped += 1
                continue

            # Check if already migrated
            existing_count = db.execute(
                text("SELECT COUNT(*) FROM template_well_definitions WHERE template_id = :tid"),
                {"tid": tmpl_id},
            ).scalar()
            if existing_count > 0:
                print(f"  Template {tmpl_id}: already migrated ({existing_count} wells). Skipping.")
                skipped += 1
                continue

            rows_to_insert = []
            for well_pos, well_data in wells.items():
                rows_to_insert.append({
                    "id":                  str(uuid.uuid4()),
                    "template_id":         str(tmpl_id),
                    "well_position":       well_pos,
                    "sample_role":         well_data.get("sample_role"),
                    "concentration_value": well_data.get("concentration_value"),
                    "concentration_unit":  well_data.get("concentration_unit"),
                    "replicate_group":     well_data.get("replicate_group"),
                    "client_id":           str(client_id) if client_id else None,
                })

            if rows_to_insert:
                db.execute(
                    text("""
                        INSERT INTO template_well_definitions
                            (id, template_id, well_position, sample_role,
                             concentration_value, concentration_unit, replicate_group, client_id)
                        VALUES
                            (:id, :template_id, :well_position, :sample_role,
                             :concentration_value, :concentration_unit, :replicate_group, :client_id)
                        ON CONFLICT (template_id, well_position) DO NOTHING
                    """),
                    rows_to_insert,
                )
                print(f"  Template {tmpl_id}: inserted {len(rows_to_insert)} well definitions.")
                migrated += 1

        db.commit()
        print(f"\nMigration complete: {migrated} templates migrated, {skipped} skipped.")

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
