"""P0 atomic-receive lookups. Resolve 0058 entities by name, not by seed string ids.

Do not insert receive samples here. parent_sample_id stays out of P0.
"""
from pathlib import Path
import json

from models.user import User
from models.project import Project, ProjectUser
from models.analysis import Analysis, Analyte
from models.list import ListEntry, List
from models.result import Result

PAYLOADS_PATH = (
    Path(__file__).resolve().parents[3]
    / "UAT_Scripts"
    / "atomic-receive"
    / "payloads.json"
)

ALICE = "alice-tech"
BOB = "bob-tech"
CAROL = "carol-manager"
MAB_PROJECT = "mAb-2301 PK Study"
CART_PROJECT = "CAR-T In-Process Testing"
ELISA = "ELISA (Human IgG)"
VIABILITY = "Cell Viability (Trypan Blue)"
IGG = "IgG Concentration"
CELL_COUNT = "Total Cell Count"
AVAILABLE = "Available for Testing"
ASSIGNED_PENDING = "Assigned/Pending"
LOD = "<LOD"
ND = "ND"

NBIO_BARCODES = [f"NBIO-AR-{i:04d}" for i in range(1, 25)]
CART_BARCODES = [f"CART-AR-{i:04d}" for i in range(1, 9)]


def load_payloads() -> dict:
    return json.loads(PAYLOADS_PATH.read_text())


def user_by_username(session, username: str) -> User:
    return session.query(User).filter(User.username == username).one()


def project_by_name(session, name: str) -> Project:
    return session.query(Project).filter(Project.name == name).one()


def analysis_by_name(session, name: str) -> Analysis:
    return session.query(Analysis).filter(Analysis.name == name).one()


def analyte_by_name(session, name: str) -> Analyte:
    return session.query(Analyte).filter(Analyte.name == name).one()


def list_entry(session, list_name: str, entry_name: str) -> ListEntry:
    return (
        session.query(ListEntry)
        .join(List, ListEntry.list_id == List.id)
        .filter(List.name == list_name, ListEntry.name == entry_name)
        .one()
    )


def project_ids_for(session, username: str) -> set:
    user = user_by_username(session, username)
    rows = session.query(ProjectUser.project_id).filter(ProjectUser.user_id == user.id).all()
    return {row[0] for row in rows}


def result_has_no_unit_id() -> bool:
    return not hasattr(Result, "unit_id")
