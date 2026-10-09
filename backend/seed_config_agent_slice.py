#!/usr/bin/env python3
"""Opt-in seed for the configuring-agent slice (fresh databases only).

This is not an Alembic migration. 0058, 0059, and 0068 already run on every
database, including dogfood. This loader writes only when ``--apply`` is
passed, and a second run refuses without changing rows.

What it adds
------------
* Whole-blood intake on existing project ``Project Alpha``, sample type
  ``Blood``, matrix ``Whole Blood``, vessel type ``K2EDTA Tube (5mL)``.
  The sample name comes from the active sample name template
  (``{PROJECT}-{SEQ}``) via atomic receive.
* Genomic DNA daughter, sample type ``DNA``, minted by
  ``AliquotPlanService.execute`` so the 0068 catalog row
  Blood × aliquot → DNA is the gate. ``parent_sample_id`` points at the
  blood sample. The product names that daughter ``{parent}-ALQ-{hex}``;
  this loader then renames it with the same sample template so the
  committed manifest can name it. Matrix is set to existing ``Genomic DNA``
  after execute, because execute copies the parent matrix.
* Users ``results-reviewer`` (existing role Lab Manager) and
  ``schema-editor`` (new role Schema Editor holding ``schema:edit`` and
  ``config:edit``). Neither is Administrator. ``admin``, ``lab-tech``, and
  ``alice-tech`` are not modified.

Passwords are bcrypt hashes (``get_password_hash``), ``must_change_password``
false. ``SLICE_REVIEWER_PASSWORD`` and ``SLICE_SCHEMA_EDITOR_PASSWORD`` supply
them. If a variable is unset, ``--apply`` generates a strong random password
for that user and prints it once on stdout. ``--check`` never prints a
password. The value is not written to a file.

Usage
-----
  # no writes
  python seed_config_agent_slice.py

  # load onto the database pointed at by MIGRATE_DATABASE_URL
  python seed_config_agent_slice.py --apply

  # re-read the slice and parse the LAL packet
  python seed_config_agent_slice.py --check
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import warnings
from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import UUID

backend_dir = Path(__file__).resolve().parent
repo_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))

warnings.filterwarnings("ignore", category=Warning, module="sqlalchemy")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import models  # noqa: F401  (register mappers)
from app.core.dev_passwords import generate_dev_password
from app.core.name_generation import generate_name_for_sample
from app.core.security import get_password_hash
from app.database import set_rls_context
from app.schemas.aliquot_plan import AliquotExecuteRequest, AliquotPlanLine
from app.schemas.sample import SampleReceiveRequest
from app.services.aliquot_plan_service import AliquotPlanService
from app.services.atomic_receive_service import receive_sample
from app.services.instrument_data_service import InstrumentDataService
from models.container import Container, ContainerType, Contents
from models.entry import Entry
from models.experiment import Experiment, ExperimentSampleExecution
from models.list import List, ListEntry
from models.project import Project, ProjectUser
from models.sample import Sample, SampleTypeTransition
from models.unit import Unit
from models.user import Permission, Role, User

REVIEWER_USERNAME = "results-reviewer"
REVIEWER_PASSWORD_ENV = "SLICE_REVIEWER_PASSWORD"
SCHEMA_PASSWORD_ENV = "SLICE_SCHEMA_EDITOR_PASSWORD"
SCHEMA_USERNAME = "schema-editor"
SCHEMA_ROLE_NAME = "Schema Editor"
REVIEWER_ROLE_NAME = "Lab Manager"
PROJECT_NAME = "Project Alpha"
CLIENT_NAME = "NovaBio Therapeutics"
BLOOD_BARCODE = "NBIO-EDTA-2310-001"
DNA_BARCODE = "NBIO-DNA-2310-001"
BLOOD_NAME = "Project Alpha-01"
DNA_NAME = "Project Alpha-02"
EXPERIMENT_NAME = "config-agent-slice-blood-dna"
BLOOD_AMOUNT = Decimal("600")
DNA_AMOUNT = Decimal("400")
TRANSFER_AMOUNT = 600.0
EDTA_TYPE_NAME = "K2EDTA Tube (5mL)"
DNA_TUBE_TYPE_NAME = "Microcentrifuge Tube (1.5mL)"
PACKET_DIR = repo_root / "UAT_Scripts" / "config-agent-slice"
LAL_DIR = repo_root / "UAT_Scripts" / "instrument-exports" / "lal-kinetic-chromogenic"
UNTOUCHED_USERS = ("admin", "lab-tech", "alice-tech")

SLICE_ERROR = 2


class SliceError(RuntimeError):
    """Refused or failed slice load. The database is left unchanged when possible."""


def _generate_slice_password() -> str:
    """Strong random password. Meets the app complexity rules. Not logged."""
    return generate_dev_password()


def _slice_passwords() -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    """Resolve slice passwords. Generated triples are (username, env name, password)."""
    generated: list[tuple[str, str, str]] = []
    passwords: dict[str, str] = {}
    for username, env_name in (
        (REVIEWER_USERNAME, REVIEWER_PASSWORD_ENV),
        (SCHEMA_USERNAME, SCHEMA_PASSWORD_ENV),
    ):
        raw = os.getenv(env_name)
        if raw:
            passwords[username] = raw
            continue
        password = _generate_slice_password()
        passwords[username] = password
        generated.append((username, env_name, password))
    return passwords, generated


def _print_generated_passwords(generated: list[tuple[str, str, str]]) -> None:
    """Stdout once, and only after a successful --apply. Never written to a file."""
    for username, env_name, password in generated:
        print(
            f"Generated password for {username} "
            f"({env_name} was unset; printed once):"
        )
        print(password)


def _owner_url() -> str:
    url = os.getenv("MIGRATE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SliceError(
            "Set MIGRATE_DATABASE_URL to the migrator owner connection. "
            "DATABASE_URL is accepted only when the migrator URL is unset."
        )
    return url


def _connect() -> tuple[Session, object]:
    url = _owner_url()
    host = url.split("@")[-1] if "@" in url else url
    user = "unknown"
    if "://" in url and "@" in url:
        user = url.split("://", 1)[1].split(":", 1)[0]
    print(f"Connecting as DB user '{user}' → {host}")
    if user == "lims_app":
        print(
            "WARNING: connected as lims_app. RLS can hide rows. "
            "Set MIGRATE_DATABASE_URL to the migrator owner."
        )
    engine = create_engine(url)
    session = sessionmaker(bind=engine)()
    return session, engine


def _list_names(list_name: str) -> tuple[str, ...]:
    """0007 stores catalog lists as slugs. Callers may pass either form."""
    slug = list_name.strip().lower().replace(" ", "_").replace("-", "_")
    names = []
    for name in (list_name, slug):
        if name and name not in names:
            names.append(name)
    return tuple(names)


def _list_entry(db: Session, list_name: str, entry_name: str) -> ListEntry:
    row = (
        db.query(ListEntry)
        .join(List, List.id == ListEntry.list_id)
        .filter(List.name.in_(_list_names(list_name)), ListEntry.name == entry_name)
        .first()
    )
    if row is None:
        raise SliceError(f"Missing list entry {list_name} / {entry_name}")
    return row


def _fingerprint(db: Session) -> list[tuple]:
    rows = db.execute(
        text(
            """
            SELECT username, role_id::text, password_hash, client_id::text
            FROM users
            WHERE username IN ('admin', 'lab-tech', 'alice-tech')
            ORDER BY username
            """
        )
    ).fetchall()
    return [tuple(row) for row in rows]


def _alice_projects(db: Session) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT p.name
            FROM project_users pu
            JOIN users u ON u.id = pu.user_id
            JOIN projects p ON p.id = pu.project_id
            WHERE u.username = 'alice-tech'
            ORDER BY p.name
            """
        )
    ).fetchall()
    return [row[0] for row in rows]


def _t0_amount(db: Session) -> Optional[Decimal]:
    row = db.execute(
        text(
            """
            SELECT c.amount
            FROM contents c
            JOIN samples s ON s.id = c.sample_id
            WHERE s.name = 'mAb-2301-PK-T0'
            """
        )
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return Decimal(str(row[0]))


def _slice_present(db: Session) -> Optional[str]:
    user = (
        db.query(User)
        .filter(User.username.in_([REVIEWER_USERNAME, SCHEMA_USERNAME]))
        .first()
    )
    if user is not None:
        return f"user {user.username} already exists"
    barcode = (
        db.query(Container)
        .filter(Container.name.in_([BLOOD_BARCODE, DNA_BARCODE]))
        .first()
    )
    if barcode is not None:
        return f"vessel {barcode.name} already exists"
    named = (
        db.query(Sample)
        .filter(Sample.name.in_([BLOOD_NAME, DNA_NAME]))
        .first()
    )
    if named is not None:
        return f"sample {named.name} already exists"
    experiment = (
        db.query(Experiment).filter(Experiment.name == EXPERIMENT_NAME).first()
    )
    if experiment is not None:
        return f"experiment {EXPERIMENT_NAME} already exists"
    return None


def _assert_prerequisites(db: Session) -> None:
    template = db.execute(
        text(
            """
            SELECT template, seq_padding_digits
            FROM name_templates
            WHERE entity_type = 'sample' AND active = true
            """
        )
    ).fetchone()
    if template is None or template[0] != "{PROJECT}-{SEQ}" or int(template[1]) != 2:
        raise SliceError(
            "Active sample name template is not {PROJECT}-{SEQ} with padding 2. "
            "Refusing so the manifest names stay aligned with 0021."
        )
    for username in UNTOUCHED_USERS:
        if db.query(User).filter(User.username == username).first() is None:
            raise SliceError(f"Required existing user {username} is missing")
    alice = db.query(User).filter(User.username == "alice-tech").one()
    if alice.role is None or alice.role.name != "Lab Technician":
        raise SliceError("alice-tech is not Lab Technician; refusing to continue")
    projects = _alice_projects(db)
    if projects != ["Project Alpha", "mAb-2301 PK Study"]:
        raise SliceError(
            "alice-tech project grants are not the 0058 pair "
            f"(Project Alpha, mAb-2301 PK Study). Found: {projects}"
        )
    if db.query(Role).filter(Role.name == REVIEWER_ROLE_NAME).first() is None:
        raise SliceError("Lab Manager role is missing")
    if db.query(Role).filter(Role.name == "Administrator").first() is None:
        raise SliceError("Administrator role is missing")
    for perm_name in ("schema:edit", "config:edit", "result:enter", "result:review"):
        if db.query(Permission).filter(Permission.name == perm_name).first() is None:
            raise SliceError(f"Permission {perm_name} is missing")
    project = db.query(Project).filter(Project.name == PROJECT_NAME).first()
    if project is None or project.client is None or project.client.name != CLIENT_NAME:
        raise SliceError(f"{PROJECT_NAME} is not on client {CLIENT_NAME}")
    blood_type = _list_entry(db, "Sample Types", "Blood")
    dna_type = _list_entry(db, "Sample Types", "DNA")
    _list_entry(db, "Matrix Types", "Whole Blood")
    _list_entry(db, "Matrix Types", "Genomic DNA")
    _list_entry(db, "Sample Status", "Available for Testing")
    edta = db.query(ContainerType).filter(ContainerType.name == EDTA_TYPE_NAME).first()
    tube = (
        db.query(ContainerType).filter(ContainerType.name == DNA_TUBE_TYPE_NAME).first()
    )
    if edta is None or not edta.is_single_position:
        raise SliceError(f"{EDTA_TYPE_NAME} is missing or is not 1×1")
    if tube is None or not tube.is_single_position:
        raise SliceError(f"{DNA_TUBE_TYPE_NAME} is missing or is not 1×1")
    if db.query(Unit).filter(Unit.name == "µL").first() is None:
        raise SliceError("Unit µL is missing")
    transition = (
        db.query(SampleTypeTransition)
        .filter(
            SampleTypeTransition.client_id == project.client_id,
            SampleTypeTransition.source_sample_type == blood_type.id,
            SampleTypeTransition.operation == "aliquot",
            SampleTypeTransition.allowed_dest_sample_type == dna_type.id,
            SampleTypeTransition.active.is_(True),
        )
        .first()
    )
    if transition is None:
        raise SliceError(
            "0068 transition Blood × aliquot → DNA is missing for "
            f"{CLIENT_NAME}. Refusing to invent one."
        )
    holders = db.execute(
        text(
            """
            SELECT u.username, r.name
            FROM users u
            JOIN roles r ON r.id = u.role_id
            JOIN role_permissions rp ON rp.role_id = r.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE p.name = 'schema:edit'
            ORDER BY u.username
            """
        )
    ).fetchall()
    non_admin = [row for row in holders if row[1] != "Administrator"]
    if non_admin:
        names = ", ".join(f"{row[0]} ({row[1]})" for row in non_admin)
        raise SliceError(
            "A non-Administrator user already holds schema:edit "
            f"({names}). Reuse that user instead of seeding schema-editor."
        )


def _cleanup(db: Session) -> None:
    """Remove a partial slice after receive has already committed."""
    params = {
        "exp": EXPERIMENT_NAME,
        "blood": BLOOD_NAME,
        "dna": DNA_NAME,
        "b": BLOOD_BARCODE,
        "d": DNA_BARCODE,
    }
    db.execute(
        text(
            """
            CREATE TEMP TABLE IF NOT EXISTS _slice_sample_ids (id uuid PRIMARY KEY)
            ON COMMIT DROP
            """
        )
    )
    db.execute(text("DELETE FROM _slice_sample_ids"))
    db.execute(
        text(
            """
            INSERT INTO _slice_sample_ids (id)
            SELECT DISTINCT s.id
            FROM samples s
            LEFT JOIN contents c ON c.sample_id = s.id
            LEFT JOIN containers k ON k.id = c.container_id
            WHERE s.name IN (:blood, :dna)
               OR k.name IN (:b, :d)
            ON CONFLICT DO NOTHING
            """
        ),
        params,
    )
    db.execute(
        text(
            """
            INSERT INTO _slice_sample_ids (id)
            SELECT s.id
            FROM samples s
            WHERE s.parent_sample_id IN (SELECT id FROM _slice_sample_ids)
            ON CONFLICT DO NOTHING
            """
        )
    )
    db.execute(
        text(
            """
            DELETE FROM experiment_sample_executions
            WHERE experiment_id IN (SELECT id FROM experiments WHERE name = :exp)
               OR sample_id IN (SELECT id FROM _slice_sample_ids)
            """
        ),
        params,
    )
    db.execute(
        text(
            """
            DELETE FROM entries
            WHERE experiment_id IN (SELECT id FROM experiments WHERE name = :exp)
            """
        ),
        params,
    )
    db.execute(
        text("DELETE FROM experiments WHERE name = :exp"),
        params,
    )
    db.execute(
        text(
            """
            DELETE FROM contents
            WHERE sample_id IN (SELECT id FROM _slice_sample_ids)
               OR container_id IN (SELECT id FROM containers WHERE name IN (:b, :d))
            """
        ),
        params,
    )
    db.execute(
        text("DELETE FROM samples WHERE id IN (SELECT id FROM _slice_sample_ids)")
    )
    db.execute(
        text("DELETE FROM containers WHERE name IN (:b, :d)"),
        params,
    )
    db.execute(
        text(
            """
            DELETE FROM project_users
            WHERE user_id IN (
                SELECT id FROM users
                WHERE username IN (:reviewer, :editor)
            )
            """
        ),
        {"reviewer": REVIEWER_USERNAME, "editor": SCHEMA_USERNAME},
    )
    db.execute(
        text(
            "DELETE FROM users WHERE username IN (:reviewer, :editor)"
        ),
        {"reviewer": REVIEWER_USERNAME, "editor": SCHEMA_USERNAME},
    )
    db.execute(
        text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (SELECT id FROM roles WHERE name = :role)
              AND NOT EXISTS (
                SELECT 1 FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE r.name = :role
              )
            """
        ),
        {"role": SCHEMA_ROLE_NAME},
    )
    db.execute(
        text(
            """
            DELETE FROM roles
            WHERE name = :role
              AND NOT EXISTS (
                SELECT 1 FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE r.name = :role
              )
            """
        ),
        {"role": SCHEMA_ROLE_NAME},
    )
    db.commit()


def _grant(db: Session, role: Role, permission_name: str) -> None:
    perm = db.query(Permission).filter(Permission.name == permission_name).one()
    db.execute(
        text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (:role_id, :perm_id)
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ),
        {"role_id": str(role.id), "perm_id": str(perm.id)},
    )


def _apply(db: Session, passwords: dict[str, str]) -> None:
    marker = _slice_present(db)
    if marker:
        raise SliceError(
            f"Refusing second run: {marker}. No rows were changed."
        )
    _assert_prerequisites(db)
    before_users = _fingerprint(db)
    before_alice = _alice_projects(db)
    before_t0 = _t0_amount(db)
    before_sample_count = db.execute(text("SELECT count(*) FROM samples")).scalar()

    project = db.query(Project).filter(Project.name == PROJECT_NAME).one()
    client = project.client
    admin = db.query(User).filter(User.username == "admin").one()
    lab_manager = db.query(Role).filter(Role.name == REVIEWER_ROLE_NAME).one()
    blood_type = _list_entry(db, "Sample Types", "Blood")
    dna_type = _list_entry(db, "Sample Types", "DNA")
    whole_blood = _list_entry(db, "Matrix Types", "Whole Blood")
    genomic_dna = _list_entry(db, "Matrix Types", "Genomic DNA")
    available = _list_entry(db, "Sample Status", "Available for Testing")
    edta = db.query(ContainerType).filter(ContainerType.name == EDTA_TYPE_NAME).one()
    dna_tube = (
        db.query(ContainerType).filter(ContainerType.name == DNA_TUBE_TYPE_NAME).one()
    )
    microliter = db.query(Unit).filter(Unit.name == "µL").one()

    schema_role = Role(
        name=SCHEMA_ROLE_NAME,
        description=(
            "Slice role with schema:edit and config:edit. Not Administrator."
        ),
        active=True,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db.add(schema_role)
    db.flush()
    _grant(db, schema_role, "schema:edit")
    _grant(db, schema_role, "config:edit")

    reviewer = User(
        name="Results Reviewer",
        username=REVIEWER_USERNAME,
        email="results-reviewer@lims.example.com",
        password_hash=get_password_hash(passwords[REVIEWER_USERNAME]),
        role_id=lab_manager.id,
        client_id=client.id,
        active=True,
        must_change_password=False,
        created_by=admin.id,
        modified_by=admin.id,
    )
    editor = User(
        name="Schema Editor",
        username=SCHEMA_USERNAME,
        email="schema-editor@lims.example.com",
        password_hash=get_password_hash(passwords[SCHEMA_USERNAME]),
        role_id=schema_role.id,
        client_id=client.id,
        active=True,
        must_change_password=False,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db.add(reviewer)
    db.add(editor)
    db.flush()
    for person in (reviewer, editor):
        db.add(
            ProjectUser(
                project_id=project.id,
                user_id=person.id,
                granted_by=admin.id,
            )
        )
    db.flush()

    set_rls_context(db, user_id=str(admin.id), client_id=str(admin.client_id))
    received = receive_sample(
        db,
        SampleReceiveRequest(
            container_barcode=BLOOD_BARCODE,
            sample_type=blood_type.id,
            project_id=project.id,
            container_type_id=edta.id,
            analysis_ids=[],
            temperature=4.0,
        ),
        admin,
    )
    if received.sample_name != BLOOD_NAME:
        raise SliceError(
            f"Atomic receive named the blood sample {received.sample_name!r}, "
            f"expected {BLOOD_NAME!r} from the sample template. Cleaned up."
        )
    if received.tests:
        raise SliceError("Atomic receive created tests. Cleaned up.")

    blood = db.query(Sample).filter(Sample.id == received.sample_id).one()
    blood.matrix = whole_blood.id
    blood.description = (
        "Whole blood intake for CMDL-SOP2310. "
        "Sample type Blood, matrix Whole Blood, first vessel only."
    )
    blood_contents = (
        db.query(Contents).filter(Contents.sample_id == blood.id).one()
    )
    blood_vessel = (
        db.query(Container).filter(Container.id == blood_contents.container_id).one()
    )
    blood_contents.amount = BLOOD_AMOUNT
    blood_contents.amount_units = microliter.id
    blood_vessel.amount = BLOOD_AMOUNT
    blood_vessel.amount_units = microliter.id
    db.flush()

    experiment = Experiment(
        name=EXPERIMENT_NAME,
        description=(
            "Slice scaffolding so AliquotPlanService.execute can mint the "
            "DNA daughter through the 0068 Blood × aliquot → DNA transition. "
            "Not a KingFisher process and not a Qubit run."
        ),
        active=True,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db.add(experiment)
    db.flush()
    db.add(
        ExperimentSampleExecution(
            experiment_id=experiment.id,
            sample_id=blood.id,
            replicate_number=1,
            processing_conditions={"source": "config-agent-slice"},
            created_by=admin.id,
            modified_by=admin.id,
        )
    )
    entry = Entry(
        experiment_id=experiment.id,
        entry_type="predefined_action",
        name="Blood to DNA",
        description="0068 aliquot execute for the config-agent slice.",
        predefined_entry_key="aliquot_pool_plan",
        sort_order=0,
        config={
            "method": "aliquot_by_target_amount",
            "default_dest_sample_type": str(dna_type.id),
            "default_dest_container_type": str(dna_tube.id),
        },
        active=True,
        created_by=admin.id,
        modified_by=admin.id,
    )
    db.add(entry)
    db.flush()

    service = AliquotPlanService(db, current_user=admin, auto_commit=False)
    executed = service.execute(
        entry.id,
        AliquotExecuteRequest(
            dry_run=False,
            lines=[
                AliquotPlanLine(
                    line_id="blood-to-dna",
                    source_sample_id=blood.id,
                    source_container_id=blood_vessel.id,
                    target_amount=TRANSFER_AMOUNT,
                    amount_unit_id=microliter.id,
                    dest_sample_type=dna_type.id,
                    inherit_entry_dest_sample_type=False,
                    dest_container_type_id=dna_tube.id,
                    inherit_entry_dest_container_type=False,
                    dest_container_name=DNA_BARCODE,
                )
            ],
        ),
    )
    if executed.error_count or executed.success_count != 1:
        raise SliceError(f"Aliquot execute did not succeed: {executed.results}")
    dest_id = executed.results[0].dest_sample_id
    if dest_id is None:
        raise SliceError("Aliquot execute returned no destination sample")
    dna = db.query(Sample).filter(Sample.id == dest_id).one()
    if dna.sample_type != dna_type.id:
        raise SliceError("Destination sample type is not DNA")
    if dna.parent_sample_id != blood.id:
        raise SliceError("Destination parent_sample_id is not the blood sample")
    product_name = dna.name
    templated = generate_name_for_sample(db, project_id=str(project.id))
    if templated != DNA_NAME:
        raise SliceError(
            f"Sample template produced {templated!r} for the daughter, "
            f"expected {DNA_NAME!r}."
        )
    dna.name = templated
    dna.matrix = genomic_dna.id
    dna.description = (
        f"Genomic DNA daughter minted by aliquot execute from {BLOOD_NAME} "
        f"(product name was {product_name}). Sample type DNA, "
        "matrix Genomic DNA, parent_sample_id set."
    )
    dna_contents = db.query(Contents).filter(Contents.sample_id == dna.id).one()
    dna_vessel = (
        db.query(Container).filter(Container.id == dna_contents.container_id).one()
    )
    if dna_vessel.name != DNA_BARCODE:
        raise SliceError(f"DNA vessel name is {dna_vessel.name!r}")
    # Execute transfers 600 µL onto the daughter (1:1). Eluate yield is 400 µL.
    # Restore the intake so the vessel still holds one 600 µL extraction.
    debited = Decimal(str(blood_contents.amount))
    dna_contents.amount = DNA_AMOUNT
    dna_contents.amount_units = microliter.id
    dna_vessel.amount = DNA_AMOUNT
    dna_vessel.amount_units = microliter.id
    dna_vessel.type_id = dna_tube.id
    blood_contents.amount = BLOOD_AMOUNT
    blood_vessel.amount = BLOOD_AMOUNT
    if blood.status != available.id or dna.status != available.id:
        raise SliceError("Receive or execute did not leave Available for Testing")
    db.commit()

    after_users = _fingerprint(db)
    after_alice = _alice_projects(db)
    after_t0 = _t0_amount(db)
    after_sample_count = db.execute(text("SELECT count(*) FROM samples")).scalar()
    if after_users != before_users:
        raise SliceError("admin, lab-tech, or alice-tech changed during the seed")
    if after_alice != before_alice:
        raise SliceError("alice-tech project grants changed during the seed")
    if after_t0 != before_t0:
        raise SliceError("mAb-2301-PK-T0 contents amount changed during the seed")
    if after_sample_count != before_sample_count + 2:
        raise SliceError(
            f"Sample count changed by {after_sample_count - before_sample_count}, expected 2"
        )

    print("Slice loaded.")
    print(f"  blood sample: {BLOOD_NAME} vessel {BLOOD_BARCODE} amount {BLOOD_AMOUNT} µL")
    print(f"  DNA daughter: {DNA_NAME} vessel {DNA_BARCODE} amount {DNA_AMOUNT} µL")
    print(f"  execute product name (renamed): {product_name}")
    print(f"  blood contents after execute debit, before restore: {debited}")
    print(f"  users: {REVIEWER_USERNAME} ({REVIEWER_ROLE_NAME}), {SCHEMA_USERNAME} ({SCHEMA_ROLE_NAME})")
    print("  passwords: bcrypt hashes stored; values are not repeated here")
    print("  alice-tech, admin, and lab-tech were not modified")
    _print_state(db)


def _print_state(db: Session) -> None:
    rows = db.execute(
        text(
            """
            SELECT s.name,
                   st.name AS sample_type,
                   mx.name AS matrix,
                   ss.name AS status,
                   p.name AS parent,
                   k.name AS barcode,
                   ct.name AS vessel_type,
                   c.amount,
                   u.name AS unit
            FROM samples s
            JOIN list_entries st ON st.id = s.sample_type
            LEFT JOIN list_entries mx ON mx.id = s.matrix
            JOIN list_entries ss ON ss.id = s.status
            LEFT JOIN samples p ON p.id = s.parent_sample_id
            JOIN contents c ON c.sample_id = s.id
            JOIN containers k ON k.id = c.container_id
            JOIN container_types ct ON ct.id = k.type_id
            LEFT JOIN units u ON u.id = c.amount_units
            WHERE s.name IN (:blood, :dna)
            ORDER BY s.name
            """
        ),
        {"blood": BLOOD_NAME, "dna": DNA_NAME},
    ).fetchall()
    print("Samples:")
    for row in rows:
        print(
            "  "
            + " | ".join("" if value is None else str(value) for value in row)
        )
    people = db.execute(
        text(
            """
            SELECT u.username, r.name,
                   COALESCE((
                       SELECT string_agg(p.name, ', ' ORDER BY p.name)
                       FROM project_users pu
                       JOIN projects p ON p.id = pu.project_id
                       WHERE pu.user_id = u.id
                   ), '')
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.username IN (:reviewer, :editor)
            ORDER BY u.username
            """
        ),
        {"reviewer": REVIEWER_USERNAME, "editor": SCHEMA_USERNAME},
    ).fetchall()
    print("Users:")
    for row in people:
        print(f"  {row[0]} role={row[1]} projects={row[2]}")
    perms = db.execute(
        text(
            """
            SELECT u.username, perm.name
            FROM users u
            JOIN roles r ON r.id = u.role_id
            JOIN role_permissions rp ON rp.role_id = r.id
            JOIN permissions perm ON perm.id = rp.permission_id
            WHERE u.username IN (:reviewer, :editor)
              AND perm.name IN (
                'schema:edit', 'config:edit', 'result:enter', 'result:review'
              )
            ORDER BY u.username, perm.name
            """
        ),
        {"reviewer": REVIEWER_USERNAME, "editor": SCHEMA_USERNAME},
    ).fetchall()
    print("Relevant permissions:")
    for row in perms:
        print(f"  {row[0]} {row[1]}")
    admin_roles = db.execute(
        text(
            """
            SELECT u.username
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.username IN (:reviewer, :editor)
              AND r.name = 'Administrator'
            """
        ),
        {"reviewer": REVIEWER_USERNAME, "editor": SCHEMA_USERNAME},
    ).fetchall()
    if admin_roles:
        raise SliceError("Slice user has the Administrator role")


def _check_db(db: Session) -> None:
    marker = _slice_present(db)
    if marker:
        # present means a piece exists; require the full pair
        pass
    blood = db.query(Sample).filter(Sample.name == BLOOD_NAME).first()
    dna = db.query(Sample).filter(Sample.name == DNA_NAME).first()
    if blood is None or dna is None:
        raise SliceError(
            f"Slice samples missing ({BLOOD_NAME}, {DNA_NAME}). "
            "Run with --apply on a fresh migrated database."
        )
    if dna.parent_sample_id != blood.id:
        raise SliceError("DNA parent_sample_id does not point at the blood sample")
    blood_type = _list_entry(db, "Sample Types", "Blood")
    dna_type = _list_entry(db, "Sample Types", "DNA")
    whole_blood = _list_entry(db, "Matrix Types", "Whole Blood")
    genomic_dna = _list_entry(db, "Matrix Types", "Genomic DNA")
    available = _list_entry(db, "Sample Status", "Available for Testing")
    if blood.sample_type != blood_type.id or blood.matrix != whole_blood.id:
        raise SliceError("Blood sample type or matrix is wrong")
    if dna.sample_type != dna_type.id or dna.matrix != genomic_dna.id:
        raise SliceError("DNA sample type or matrix is wrong")
    if blood.status != available.id or dna.status != available.id:
        raise SliceError("Slice samples are not Available for Testing")
    for sample, barcode, amount in (
        (blood, BLOOD_BARCODE, BLOOD_AMOUNT),
        (dna, DNA_BARCODE, DNA_AMOUNT),
    ):
        contents = db.query(Contents).filter(Contents.sample_id == sample.id).all()
        if len(contents) != 1:
            raise SliceError(f"{sample.name} does not have exactly one contents row")
        vessel = db.query(Container).filter(Container.id == contents[0].container_id).one()
        if vessel.name != barcode:
            raise SliceError(f"{sample.name} vessel is {vessel.name}")
        if Decimal(str(contents[0].amount)) != amount:
            raise SliceError(f"{sample.name} contents amount is {contents[0].amount}")
        if contents[0].amount < 0:
            raise SliceError(f"{sample.name} amount is below 0")
    reviewer = db.query(User).filter(User.username == REVIEWER_USERNAME).one()
    editor = db.query(User).filter(User.username == SCHEMA_USERNAME).one()
    if reviewer.role.name != REVIEWER_ROLE_NAME:
        raise SliceError("results-reviewer role is not Lab Manager")
    if editor.role.name != SCHEMA_ROLE_NAME:
        raise SliceError("schema-editor role is not Schema Editor")
    if reviewer.role.name == "Administrator" or editor.role.name == "Administrator":
        raise SliceError("Slice user has the Administrator role")
    editor_perms = {perm.name for perm in editor.role.permissions}
    if "schema:edit" not in editor_perms or "config:edit" not in editor_perms:
        raise SliceError("schema-editor is missing schema:edit or config:edit")
    reviewer_perms = {perm.name for perm in reviewer.role.permissions}
    if "result:review" not in reviewer_perms:
        raise SliceError("results-reviewer is missing result:review")
    if "schema:edit" in reviewer_perms:
        raise SliceError("results-reviewer holds schema:edit")
    alice_projects = _alice_projects(db)
    if alice_projects != ["Project Alpha", "mAb-2301 PK Study"]:
        raise SliceError(f"alice-tech projects changed: {alice_projects}")
    t0 = _t0_amount(db)
    if t0 != Decimal("50"):
        raise SliceError(f"mAb-2301-PK-T0 contents amount is {t0}, expected 50")
    print("Database slice checks passed.")
    _print_state(db)


def _lal_config() -> dict:
    path = PACKET_DIR / "lal-parser-config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _check_lal() -> None:
    config = _lal_config()
    service = InstrumentDataService(config)
    files = sorted(LAL_DIR.glob("*.csv"))
    if len(files) != 10:
        raise SliceError(f"Expected 10 LAL CSVs, found {len(files)}")
    valid = 0
    edge = 0
    bound: set[str] = set()
    for path in files:
        report = service.parse_report(path.read_bytes())
        if not report.ok:
            raise SliceError(
                f"LAL parse failed for {path.name}: {report.hard_errors}"
            )
        classes = {row.get("example_class") for row in report.preview_rows}
        # preview is capped; re-parse rows for the class and lims_sample
        rows, _warnings, hard = service.parse(path.read_bytes(), raise_on_hard=True)
        classes = {row.row_data.get("example_class") for row in rows}
        if classes == {"valid"}:
            valid += 1
        elif classes == {"edge"}:
            edge += 1
        else:
            raise SliceError(f"{path.name} example_class set is {classes}")
        for row in rows:
            label = row.row_data.get("lims_sample")
            if label:
                bound.add(str(label))
        print(f"  LAL {path.name}: {len(rows)} rows ok")
    if valid != 8 or edge != 2:
        raise SliceError(f"LAL class counts valid={valid} edge={edge}, expected 8 and 2")
    expected = {"CAR-T-Batch-001", "Plasmid-Lot-2025-001"}
    if not expected.issubset(bound):
        raise SliceError(f"LAL lims_sample bind is {sorted(bound)}")
    print(f"LAL parse passed ({valid} valid, {edge} edge). Bound samples: {sorted(bound)}")


def _check_manifest(db: Optional[Session]) -> None:
    path = PACKET_DIR / "manifest.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 6:
        raise SliceError(f"Manifest has {len(rows)} rows, expected about 6")
    names = [row["name"] for row in rows]
    required = [
        "CAR-T-Batch-001",
        "Plasmid-Lot-2025-001",
        "mAb-2301-PK-T0",
        "mAb-2301-PK-T0-Aliq",
        "NBIO-CMPD-001",
        BLOOD_NAME,
        DNA_NAME,
    ]
    missing = [name for name in required if name not in names]
    if missing:
        raise SliceError(f"Manifest missing names: {missing}")
    sop = [row["name"] for row in rows if row["sop_path"] == "yes"]
    if sop != [BLOOD_NAME, DNA_NAME]:
        raise SliceError(f"SOP path rows are {sop}")
    depleted = [row for row in rows if row["row_role"] == "depleted_edge"]
    if len(depleted) != 1 or depleted[0]["amount"] != "0":
        raise SliceError("Manifest needs one depleted row with amount 0")
    if depleted[0]["status"] != "Testing Complete":
        raise SliceError(
            "Depleted row status is not the closest existing status Testing Complete"
        )
    if db is None:
        print("Manifest shape passed (no database to resolve names).")
        return
    for row in rows:
        if row["row_role"] == "instrument_compound":
            found = db.execute(
                text("SELECT 1 FROM samples WHERE name = :name"),
                {"name": row["name"]},
            ).fetchone()
            if found:
                raise SliceError(
                    f"{row['name']} resolved to a sample; it is an instrument compound id"
                )
            print(f"  {row['name']}: instrument compound, not a samples row")
            continue
        found = db.execute(
            text(
                """
                SELECT s.name, st.name, p.name
                FROM samples s
                JOIN list_entries st ON st.id = s.sample_type
                JOIN projects p ON p.id = s.project_id
                WHERE s.name = :name
                """
            ),
            {"name": row["name"]},
        ).fetchone()
        if found is None:
            raise SliceError(f"Manifest name {row['name']} does not resolve to a sample")
        if found[1] != row["sample_type"]:
            raise SliceError(
                f"{row['name']} sample type is {found[1]}, manifest says {row['sample_type']}"
            )
        if found[2] != row["project"]:
            raise SliceError(
                f"{row['name']} project is {found[2]}, manifest says {row['project']}"
            )
        if row["parent_name"]:
            parent = db.execute(
                text(
                    """
                    SELECT parent.name
                    FROM samples child
                    JOIN samples parent ON parent.id = child.parent_sample_id
                    WHERE child.name = :name
                    """
                ),
                {"name": row["name"]},
            ).fetchone()
            if parent is None or parent[0] != row["parent_name"]:
                raise SliceError(
                    f"{row['name']} parent is {None if parent is None else parent[0]}"
                )
        print(f"  {row['name']}: sample row ok")
    print("Manifest names passed.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the slice. Without this flag the database is not changed.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify an already loaded slice and parse the LAL packet.",
    )
    args = parser.parse_args(argv)
    if args.apply and args.check:
        print("Pass only one of --apply or --check.")
        return SLICE_ERROR
    if not args.apply and not args.check:
        print(
            "Opt-in only. No rows were written.\n"
            "  python seed_config_agent_slice.py --apply\n"
            "  python seed_config_agent_slice.py --check\n"
            "Uses MIGRATE_DATABASE_URL (migrator owner), not an Alembic revision.\n"
            "A second --apply refuses if the slice is already present.\n"
            "Passwords: SLICE_REVIEWER_PASSWORD and SLICE_SCHEMA_EDITOR_PASSWORD.\n"
            "Unset variables are generated and printed once on a successful --apply."
        )
        return 0
    if args.check:
        _check_lal()
        db, engine = _connect()
        try:
            _check_manifest(db)
            _check_db(db)
        finally:
            db.close()
            engine.dispose()
        print("Check passed.")
        return 0
    db, engine = _connect()
    started = False
    try:
        # receive_sample commits. Track that so a later failure can delete the slice.
        marker = _slice_present(db)
        if marker:
            raise SliceError(
                f"Refusing second run: {marker}. No rows were changed."
            )
        started = True
        passwords, generated = _slice_passwords()
        _apply(db, passwords)
        _print_generated_passwords(generated)
    except SliceError as exc:
        print(f"ERROR: {exc}")
        db.rollback()
        if started and "Refusing second run" not in str(exc):
            try:
                _cleanup(db)
                print("Partial slice removed.")
            except Exception as cleanup_error:  # noqa: BLE001
                print(f"Cleanup failed: {cleanup_error}")
        return SLICE_ERROR
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        db.rollback()
        if started:
            try:
                _cleanup(db)
                print("Partial slice removed.")
            except Exception as cleanup_error:  # noqa: BLE001
                print(f"Cleanup failed: {cleanup_error}")
        return 1
    finally:
        db.close()
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
