"""
Tests for aliquots and derivatives API endpoints
"""
import pytest
from decimal import Decimal
from tests._fk_helpers import scratch_entry_id, scratch_list_id, get_or_create_list_entry
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from models.sample import Sample
from models.container import Container, Contents
from models.container import ContainerType
from models.user import User
from models.user import Role
from models.user import Permission
from tests._legacy_models import RolePermission

client = TestClient(app)


# These tests were written against a since-removed conftest that provided
# `sample_user` and `auth_headers`. Recreate them on top of the shared fixtures:
# an Administrator (all permissions, passes client/project access checks).
# Not autouse: the parallel overdraw tests use db_engine only. Opening
# db_session would BEGIN a fixture transaction and fail their idle check.
@pytest.fixture
def _route_through_test_db(client):
    """Install the conftest get_db override on the shared app for the
    module-level TestClient above."""
    yield


@pytest.fixture
def sample_user(test_admin_user):
    return test_admin_user


@pytest.fixture
def auth_headers(client, test_admin_user):
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.usefixtures("_route_through_test_db")
class TestAliquotsAPI:
    """Test aliquots and derivatives API endpoints"""
    
    def test_create_aliquot(self, db_session, auth_headers, sample_user):
        """Test creating an aliquot from a parent sample"""
        # Create test data
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Aliquot",
            description="Test client for aliquot",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Aliquot",
            description="Test project for aliquot",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=scratch_entry_id(db_session),  # projects.status is NOT NULL (FK to list_entries)
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample type and status
        sample_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        sample_status = get_or_create_list_entry(db_session, "sample_status", "Available for Testing")
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Sample",
            description="Parent sample for aliquot",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(parent_sample)
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="Test Tube",
            description="Test tube container",
            capacity=5.0,
            material="Plastic",
            rows=1, columns=1,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        # Create container
        container = Container(
            name="Aliquot Container",
            description="Container for aliquot",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container)
        db_session.flush()

        source = Container(
            name="Parent Vessel",
            description="Vessel holding the parent sample",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(source)
        db_session.flush()
        db_session.add(Contents(
            container_id=source.id,
            sample_id=parent_sample.id,
            amount=Decimal("10"),
        ))
        db_session.flush()
        
        aliquot_data = {
            "parent_sample_id": str(parent_sample.id),
            "name": "Aliquot 1",
            "description": "First aliquot from parent",
            "container_id": str(container.id),
            "concentration": 10.5,
            "amount": 2.0,
            "temperature": 4.0
        }
        
        # An aliquot keeps the parent's type: a different sample_type is refused.
        other_type = ListEntry(
            name="DNA",
            description="DNA sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(other_type)
        db_session.flush()
        changed = client.post(
            "/aliquots/aliquot",
            json={**aliquot_data, "sample_type": str(other_type.id)},
            headers=auth_headers,
        )
        assert changed.status_code == 400, changed.text
        assert changed.json()["detail"]["code"] == "aliquot_type_change_not_allowed"

        response = client.post(
            "/aliquots/aliquot",
            json={**aliquot_data, "sample_type": str(sample_type.id)},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        
        data = response.json()
        assert data["id"] == str(parent_sample.id)
        assert data["name"] == "Parent Sample"
        assert data["parent_sample_id"] is None
        assert data["container_id"] == str(container.id)
        assert data["project_id"] == str(project.id)
        assert data["client_id"] == str(client_entity.id)
        assert data["source_amount_remaining"] == 8.0
        db_session.expire_all()
        assert db_session.query(Sample).filter(Sample.project_id == project.id).count() == 1
        left = db_session.query(Contents).filter(Contents.container_id == source.id).one()
        assert Decimal(left.amount) == Decimal("8")
    
    def test_create_derivative(self, db_session, auth_headers, sample_user):
        """Test creating a derivative from a parent sample"""
        # Create test data (similar to aliquot test)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Derivative",
            description="Test client for derivative",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Derivative",
            description="Test project for derivative",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=scratch_entry_id(db_session),  # projects.status is NOT NULL (FK to list_entries)
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample types and status
        blood_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(blood_type)
        db_session.flush()
        
        dna_type = ListEntry(
            name="DNA",
            description="DNA sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(dna_type)
        db_session.flush()
        
        sample_status = get_or_create_list_entry(db_session, "sample_status", "Available for Testing")
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Blood Sample",
            description="Parent blood sample for derivative",
            sample_type=blood_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(parent_sample)
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="DNA Tube",
            description="DNA tube container",
            capacity=2.0,
            material="Plastic",
            rows=8, columns=32,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        # Create container
        container = Container(
            name="Derivative Container",
            description="Container for derivative",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container)
        db_session.flush()

        source = Container(
            name="Parent Blood Vessel",
            description="Vessel holding the parent blood",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(source)
        db_session.flush()
        db_session.add(Contents(
            container_id=source.id,
            sample_id=parent_sample.id,
            amount=Decimal("10"),
        ))
        db_session.flush()
        
        derivative_data = {
            "parent_sample_id": str(parent_sample.id),
            "name": "DNA Extract",
            "description": "DNA extract from blood",
            "sample_type": str(dna_type.id),
            "container_id": str(container.id),
            "concentration": 50.0,
            "amount": 1.0,
            "temperature": -20.0
        }
        
        # No derivative transition Blood -> DNA for this client yet: refused.
        refused = client.post("/aliquots/derivative", json=derivative_data, headers=auth_headers)
        assert refused.status_code == 400, refused.text
        assert refused.json()["detail"]["code"] == "dest_sample_type_not_allowed"

        # Same type is an aliquot, not a derivative.
        same = client.post(
            "/aliquots/derivative",
            json={**derivative_data, "sample_type": str(blood_type.id)},
            headers=auth_headers,
        )
        assert same.status_code == 400, same.text
        assert same.json()["detail"]["code"] == "derivative_same_type"

        from models.sample import SampleTypeTransition
        db_session.add(SampleTypeTransition(
            client_id=client_entity.id,
            source_sample_type=blood_type.id,
            operation="derivative",
            allowed_dest_sample_type=dna_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        ))
        db_session.flush()

        response = client.post("/aliquots/derivative", json=derivative_data, headers=auth_headers)
        assert response.status_code == 200, response.text
        
        data = response.json()
        assert data["name"].startswith("Parent Blood Sample-DER-")
        assert "-ALQ-" not in data["name"]
        assert data["id"] != str(parent_sample.id)
        assert data["parent_sample_id"] == str(parent_sample.id)
        assert data["sample_type"] == str(dna_type.id)
        assert data["container_id"] == str(container.id)
        assert data["project_id"] == str(project.id)
        assert data["client_id"] == str(client_entity.id)
        assert data["source_amount_remaining"] == 9.0
        db_session.expire_all()
        left = db_session.query(Contents).filter(Contents.container_id == source.id).one()
        assert Decimal(left.amount) == Decimal("9")
        assert left.sample_id == parent_sample.id
    
    def test_pool_samples(self, db_session, auth_headers, sample_user):
        """Test pooling multiple samples in a container"""
        # Create test data
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        from models.unit import Unit
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Pooling",
            description="Test client for pooling",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Pooling",
            description="Test project for pooling",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=scratch_entry_id(db_session),  # projects.status is NOT NULL (FK to list_entries)
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample type and status
        sample_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        sample_status = get_or_create_list_entry(db_session, "sample_status", "Available for Testing")
        db_session.add(sample_status)
        db_session.flush()
        
        # Create samples
        sample1 = Sample(
            name="Sample 1",
            description="First sample for pooling",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample1)
        db_session.flush()
        
        sample2 = Sample(
            name="Sample 2",
            description="Second sample for pooling",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample2)
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="Pooling Tube",
            description="Tube for pooling samples",
            capacity=10.0,
            material="Plastic",
            rows=1, columns=1,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        # Create container
        container = Container(
            name="Pooling Container",
            description="Container for pooling",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        # Units: pooling sums amounts in the lab's base *volume* unit (list
        # entry named "volume") and averages concentration in that type's base.
        volume_type = get_or_create_list_entry(db_session, "unit_type", "volume")
        conc_type = scratch_entry_id(db_session)
        base_ml = (
            db_session.query(Unit)
            .filter(Unit.type == volume_type.id, Unit.multiplier == 1, Unit.active == True)  # noqa: E712
            .first()
        )
        if base_ml is None:
            base_ml = Unit(name=f"mL_{uuid4().hex[:4]}", description="Milliliter",
                           type=volume_type.id, multiplier=1.0)
            db_session.add(base_ml)
        mg_unit = Unit(  # volume unit: microliter
            name=f"uL_{uuid4().hex[:4]}",
            description="Microliter",
            type=volume_type.id,
            multiplier=0.001,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(mg_unit)
        db_session.flush()

        mg_ml_unit = Unit(
            name=f"mg/mL_{uuid4().hex[:4]}",
            description="Milligram per milliliter",
            type=conc_type,
            multiplier=1.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(mg_ml_unit)
        db_session.flush()

        source1 = Container(
            name=f"Pool source 1 {uuid4().hex[:6]}",
            description="source",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        source2 = Container(
            name=f"Pool source 2 {uuid4().hex[:6]}",
            description="source",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add_all([source1, source2])
        db_session.flush()
        db_session.add(Contents(
            container_id=source1.id, sample_id=sample1.id, amount=Decimal("50"), amount_units=mg_unit.id,
        ))
        db_session.add(Contents(
            container_id=source2.id, sample_id=sample2.id, amount=Decimal("50"), amount_units=mg_unit.id,
        ))
        db_session.flush()

        pooling_data = {
            "container_id": str(container.id),
            "samples": [str(sample1.id), str(sample2.id)],
            "concentrations": [10.0, 20.0],
            "concentration_units": [str(mg_ml_unit.id), str(mg_ml_unit.id)],
            "amounts": [5.0, 10.0],
            "amount_units": [str(mg_unit.id), str(mg_unit.id)],
            "notes": "Pooled samples for testing"
        }
        
        response = client.post("/aliquots/pool", json=pooling_data, headers=auth_headers)
        assert response.status_code == 200, response.text
        
        data = response.json()
        assert data["container_id"] == str(container.id)
        assert len(data["pooled_samples"]) == 2
        assert str(sample1.id) in data["pooled_samples"]
        assert str(sample2.id) in data["pooled_samples"]
        assert data["notes"] == "Pooled samples for testing"
        db_session.expire_all()
        left1 = db_session.query(Contents).filter(Contents.container_id == source1.id).one()
        left2 = db_session.query(Contents).filter(Contents.container_id == source2.id).one()
        assert Decimal(left1.amount) == Decimal("45")
        assert Decimal(left2.amount) == Decimal("40")
        dest_rows = db_session.query(Contents).filter(Contents.container_id == container.id).all()
        assert {row.sample_id for row in dest_rows} == {sample1.id, sample2.id}
        # 5 of 10 mg/mL and 10 of 20 mg/mL is 15 in the shared unit, on every destination row.
        for row in dest_rows:
            assert abs(float(row.concentration) - 15.0) < 0.001
            assert row.concentration_units == mg_ml_unit.id
    
    def test_get_aliquots_for_parent(self, db_session, auth_headers, sample_user):
        """Test getting aliquots for a parent sample"""
        # Create test data (similar to aliquot test)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Get Aliquots",
            description="Test client for getting aliquots",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Get Aliquots",
            description="Test project for getting aliquots",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=scratch_entry_id(db_session),  # projects.status is NOT NULL (FK to list_entries)
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample type and status
        sample_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        sample_status = get_or_create_list_entry(db_session, "sample_status", "Available for Testing")
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Sample for Get",
            description="Parent sample for getting aliquots",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(parent_sample)
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="Test Tube",
            description="Test tube container",
            capacity=5.0,
            material="Plastic",
            rows=1, columns=1,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        # Create containers
        container1 = Container(
            name="Aliquot Container 1",
            description="First aliquot container",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        db_session.flush()
        
        container2 = Container(
            name="Aliquot Container 2",
            description="Second aliquot container",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container2)
        db_session.flush()
        
        # An aliquot is another contents row of the same sample, not a child Sample.
        db_session.add(Contents(container_id=container1.id, sample_id=parent_sample.id, amount=Decimal("6")))
        db_session.add(Contents(container_id=container2.id, sample_id=parent_sample.id, amount=Decimal("4")))
        db_session.commit()
        
        response = client.get(f"/aliquots/parent/{parent_sample.id}", headers=auth_headers)
        assert response.status_code == 200, response.text
        
        data = response.json()
        assert len(data) == 2
        assert {item["id"] for item in data} == {str(parent_sample.id)}
        assert {item["name"] for item in data} == {"Parent Sample for Get"}
        assert {item["container_id"] for item in data} == {str(container1.id), str(container2.id)}
        assert {item["amount"] for item in data} == {6.0, 4.0}
    
    def test_get_derivatives_for_parent(self, db_session, auth_headers, sample_user):
        """Test getting derivatives for a parent sample"""
        # Create test data (similar to derivative test)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Get Derivatives",
            description="Test client for getting derivatives",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Get Derivatives",
            description="Test project for getting derivatives",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=scratch_entry_id(db_session),  # projects.status is NOT NULL (FK to list_entries)
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample types and status
        blood_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(blood_type)
        db_session.flush()
        
        dna_type = ListEntry(
            name="DNA",
            description="DNA sample",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(dna_type)
        db_session.flush()
        
        sample_status = get_or_create_list_entry(db_session, "sample_status", "Available for Testing")
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Blood Sample for Get",
            description="Parent blood sample for getting derivatives",
            sample_type=blood_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(parent_sample)
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="DNA Tube",
            description="DNA tube container",
            capacity=2.0,
            material="Plastic",
            rows=8, columns=32,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        # Create containers
        container1 = Container(
            name="Derivative Container 1",
            description="First derivative container",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        db_session.flush()
        
        container2 = Container(
            name="Derivative Container 2",
            description="Second derivative container",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container2)
        db_session.flush()
        
        # Create derivatives
        derivative1 = Sample(
            name="DNA Extract 1",
            description="First DNA extract",
            sample_type=dna_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            parent_sample_id=parent_sample.id,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(derivative1)
        db_session.flush()
        
        derivative2 = Sample(
            name="DNA Extract 2",
            description="Second DNA extract",
            sample_type=dna_type.id,
            status=sample_status.id,
            matrix=scratch_entry_id(db_session),  # NOT NULL FK to list_entries
            parent_sample_id=parent_sample.id,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(derivative2)
        db_session.flush()
        
        # Create contents entries
        contents1 = Contents(
            container_id=container1.id,
            sample_id=derivative1.id
        )
        db_session.add(contents1)
        
        contents2 = Contents(
            container_id=container2.id,
            sample_id=derivative2.id
        )
        db_session.add(contents2)
        db_session.commit()
        
        response = client.get(f"/aliquots/derivatives/{parent_sample.id}", headers=auth_headers)
        assert response.status_code == 200, response.text
        
        data = response.json()
        assert len(data) == 2
        assert any(item["name"] == "DNA Extract 1" for item in data)
        assert any(item["name"] == "DNA Extract 2" for item in data)


def _tracked_parent(db_session, user, *, label, amount="10", temperature=None):
    """Parent sample sitting in one vessel, plus an empty destination vessel."""
    from models.client import Client
    from models.list import ListEntry
    from models.project import Project

    client_entity = Client(
        name=f"Client {label} {uuid4().hex[:6]}",
        description=label,
        billing_info={},
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(client_entity)
    db_session.flush()
    project = Project(
        name=f"Project {label} {uuid4().hex[:6]}",
        description=label,
        start_date="2024-01-01",
        client_id=client_entity.id,
        status=scratch_entry_id(db_session),
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(project)
    db_session.flush()
    sample_type = ListEntry(
        name=f"Blood {uuid4().hex[:6]}",
        description="Blood",
        list_id=scratch_list_id(db_session),
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(sample_type)
    db_session.flush()
    sample_status = get_or_create_list_entry(db_session, "sample_status", "Available for Testing")
    parent = Sample(
        name=f"Parent {label} {uuid4().hex[:6]}",
        description=label,
        sample_type=sample_type.id,
        status=sample_status.id,
        matrix=scratch_entry_id(db_session),
        project_id=project.id,
        temperature=temperature,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(parent)
    db_session.flush()
    container_type = ContainerType(
        name=f"Tube {label} {uuid4().hex[:6]}",
        description="tube",
        capacity=10.0,
        material="Plastic",
        rows=1,
        columns=1,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add(container_type)
    db_session.flush()
    source = Container(
        name=f"SRC {label} {uuid4().hex[:6]}",
        description="source",
        type_id=container_type.id,
        created_by=user.id,
        modified_by=user.id,
    )
    dest = Container(
        name=f"DST {label} {uuid4().hex[:6]}",
        description="dest",
        type_id=container_type.id,
        created_by=user.id,
        modified_by=user.id,
    )
    db_session.add_all([source, dest])
    db_session.flush()
    db_session.add(Contents(
        container_id=source.id,
        sample_id=parent.id,
        amount=None if amount is None else Decimal(amount),
    ))
    db_session.flush()
    return {
        "client": client_entity,
        "project": project,
        "parent": parent,
        "sample_type": sample_type,
        "source": source,
        "dest": dest,
        "container_type": container_type,
    }


@pytest.mark.usefixtures("_route_through_test_db")
class TestAliquotAmountConservation:
    """Amount stays conserved: debit the source, never insert free volume, never delete."""

    def test_aliquot_conserves_amount_and_creates_no_sample(
        self, db_session, auth_headers, sample_user
    ):
        lab = _tracked_parent(db_session, sample_user, label="conserve")
        parent = lab["parent"]
        before = db_session.query(Sample).count()
        body = {
            "parent_sample_id": str(parent.id),
            "container_id": str(lab["dest"].id),
            "amount": 6,
        }
        first = client.post("/aliquots", json=body, headers=auth_headers)
        assert first.status_code == 200, first.text
        payload = first.json()
        assert payload["id"] == str(parent.id)
        assert payload["source_amount_remaining"] == 4.0
        assert payload["amount"] == 6.0
        assert payload["container_id"] == str(lab["dest"].id)

        db_session.expire_all()
        assert db_session.query(Sample).count() == before
        source_row = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
        dest_row = db_session.query(Contents).filter(Contents.container_id == lab["dest"].id).one()
        assert Decimal(source_row.amount) == Decimal("4")
        assert dest_row.sample_id == parent.id
        assert Decimal(dest_row.amount) == Decimal("6")
        assert db_session.query(Sample).filter(Sample.id == parent.id).one().active is True

        second_dest = Container(
            name=f"DST2 {uuid4().hex[:6]}",
            description="second",
            type_id=lab["container_type"].id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(second_dest)
        db_session.flush()
        emptied = client.post(
            "/aliquots/aliquot",
            json={
                "parent_sample_id": str(parent.id),
                "container_id": str(second_dest.id),
                "source_container_id": str(lab["source"].id),
                "amount": 4,
            },
            headers=auth_headers,
        )
        assert emptied.status_code == 200, emptied.text
        assert emptied.json()["source_amount_remaining"] == 0.0
        db_session.expire_all()
        source_row = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
        assert Decimal(source_row.amount) == Decimal("0")
        assert db_session.query(Sample).filter(Sample.id == parent.id).one().active is True
        assert db_session.query(Sample).count() == before

    def test_overdraw_and_null_amount_refused(self, db_session, auth_headers, sample_user):
        lab = _tracked_parent(db_session, sample_user, label="overdraw")
        parent = lab["parent"]
        over = client.post(
            "/aliquots",
            json={
                "parent_sample_id": str(parent.id),
                "container_id": str(lab["dest"].id),
                "amount": 11,
            },
            headers=auth_headers,
        )
        assert over.status_code == 400, over.text
        assert over.json()["detail"]["code"] == "insufficient_amount"
        assert "Insufficient" in over.json()["detail"]["message"]
        missing = client.post(
            "/aliquots",
            json={"parent_sample_id": str(parent.id), "container_id": str(lab["dest"].id)},
            headers=auth_headers,
        )
        assert missing.status_code == 400, missing.text
        assert missing.json()["detail"]["code"] == "amount_required"
        db_session.expire_all()
        source_row = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
        assert Decimal(source_row.amount) == Decimal("10")
        assert (
            db_session.query(Contents).filter(Contents.container_id == lab["dest"].id).count() == 0
        )
        assert db_session.query(Sample).filter(Sample.parent_sample_id == parent.id).count() == 0

        empty = _tracked_parent(db_session, sample_user, label="nullamt", amount=None)
        refused = client.post(
            "/aliquots",
            json={
                "parent_sample_id": str(empty["parent"].id),
                "container_id": str(empty["dest"].id),
                "amount": 1,
            },
            headers=auth_headers,
        )
        assert refused.status_code == 400, refused.text
        assert refused.json()["detail"]["code"] == "source_amount_null"

    def test_derivative_conserves_amount_and_uses_der_name(
        self, db_session, auth_headers, sample_user
    ):
        from models.list import ListEntry
        from models.sample import SampleTypeTransition

        lab = _tracked_parent(db_session, sample_user, label="deriv")
        parent = lab["parent"]
        dna = ListEntry(
            name=f"DNA {uuid4().hex[:6]}",
            description="DNA",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(dna)
        db_session.flush()
        over = client.post(
            "/aliquots/derivative",
            json={
                "parent_sample_id": str(parent.id),
                "name": "should-not-stick",
                "sample_type": str(dna.id),
                "container_id": str(lab["dest"].id),
                "amount": 11,
            },
            headers=auth_headers,
        )
        assert over.status_code == 400, over.text
        assert over.json()["detail"]["code"] == "dest_sample_type_not_allowed"
        db_session.add(SampleTypeTransition(
            client_id=lab["client"].id,
            source_sample_type=lab["sample_type"].id,
            operation="derivative",
            allowed_dest_sample_type=dna.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        ))
        db_session.flush()
        over = client.post(
            "/aliquots/derivative",
            json={
                "parent_sample_id": str(parent.id),
                "name": "should-not-stick",
                "sample_type": str(dna.id),
                "container_id": str(lab["dest"].id),
                "amount": 11,
            },
            headers=auth_headers,
        )
        assert over.status_code == 400, over.text
        assert over.json()["detail"]["code"] == "insufficient_amount"
        db_session.expire_all()
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one().amount
        ) == Decimal("10")
        assert db_session.query(Sample).filter(Sample.parent_sample_id == parent.id).count() == 0

        created = client.post(
            "/aliquots/derivative",
            json={
                "parent_sample_id": str(parent.id),
                "name": "DNA Extract",
                "description": "from blood",
                "sample_type": str(dna.id),
                "container_id": str(lab["dest"].id),
                "amount": 3,
            },
            headers=auth_headers,
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        assert payload["name"].startswith(f"{parent.name}-DER-")
        assert "-ALQ-" not in payload["name"]
        assert payload["id"] != str(parent.id)
        assert payload["parent_sample_id"] == str(parent.id)
        assert payload["description"] == "from blood"
        assert payload["source_amount_remaining"] == 7.0
        db_session.expire_all()
        child = db_session.query(Sample).filter(Sample.id == payload["id"]).one()
        assert "-DER-" in child.name and "-ALQ-" not in child.name
        source_row = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
        dest_row = db_session.query(Contents).filter(Contents.container_id == lab["dest"].id).one()
        assert Decimal(source_row.amount) == Decimal("7")
        assert dest_row.sample_id == child.id
        assert Decimal(dest_row.amount) == Decimal("3")
        assert db_session.query(Sample).filter(Sample.id == parent.id).one().active is True

    def test_derivative_temperature_zero_is_stored(
        self, db_session, auth_headers, sample_user
    ):
        from models.list import ListEntry
        from models.sample import SampleTypeTransition

        lab = _tracked_parent(db_session, sample_user, label="temp0", temperature=Decimal("4"))
        parent = lab["parent"]
        dna = ListEntry(
            name=f"DNA {uuid4().hex[:6]}",
            description="DNA",
            list_id=scratch_list_id(db_session),
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(dna)
        db_session.flush()
        db_session.add(SampleTypeTransition(
            client_id=lab["client"].id,
            source_sample_type=lab["sample_type"].id,
            operation="derivative",
            allowed_dest_sample_type=dna.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        ))
        db_session.flush()
        body = {
            "parent_sample_id": str(parent.id),
            "name": "ice",
            "sample_type": str(dna.id),
            "container_id": str(lab["dest"].id),
            "amount": 1,
            "temperature": 0,
        }
        frozen = client.post("/aliquots/derivative", json=body, headers=auth_headers)
        assert frozen.status_code == 200, frozen.text
        assert frozen.json()["temperature"] == 0.0
        child = db_session.query(Sample).filter(Sample.id == frozen.json()["id"]).one()
        assert child.temperature == Decimal("0")

        omitted = _tracked_parent(
            db_session, sample_user, label="tempblank", temperature=Decimal("0")
        )
        blank_dest = omitted["dest"]
        db_session.add(SampleTypeTransition(
            client_id=omitted["client"].id,
            source_sample_type=omitted["sample_type"].id,
            operation="derivative",
            allowed_dest_sample_type=dna.id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        ))
        db_session.flush()
        inherited = client.post(
            "/aliquots/derivative",
            json={
                "parent_sample_id": str(omitted["parent"].id),
                "name": "blank",
                "sample_type": str(dna.id),
                "container_id": str(blank_dest.id),
                "amount": 1,
            },
            headers=auth_headers,
        )
        assert inherited.status_code == 200, inherited.text
        assert inherited.json()["temperature"] == 0.0

    def test_pool_overdraw_debits_nothing(self, db_session, auth_headers, sample_user):
        from models.unit import Unit

        rich = _tracked_parent(db_session, sample_user, label="poolrich")
        poor = _tracked_parent(db_session, sample_user, label="poolpoor", amount="3")
        volume_type = get_or_create_list_entry(db_session, "unit_type", "volume")
        conc_type = scratch_entry_id(db_session)
        amount_unit = (
            db_session.query(Unit)
            .filter(Unit.type == volume_type.id, Unit.multiplier == 1, Unit.active == True)  # noqa: E712
            .first()
        )
        if amount_unit is None:
            amount_unit = Unit(
                name=f"mL_{uuid4().hex[:4]}",
                description="mL",
                type=volume_type.id,
                multiplier=1.0,
            )
            db_session.add(amount_unit)
        conc_unit = Unit(
            name=f"mgmL_{uuid4().hex[:4]}",
            description="mg/mL",
            type=conc_type,
            multiplier=1.0,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(conc_unit)
        db_session.flush()
        dest = Container(
            name=f"Pool dest {uuid4().hex[:6]}",
            description="dest",
            type_id=rich["container_type"].id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(dest)
        db_session.flush()
        body = {
            "container_id": str(dest.id),
            "samples": [str(rich["parent"].id), str(poor["parent"].id)],
            "concentrations": [1.0, 1.0],
            "concentration_units": [str(conc_unit.id), str(conc_unit.id)],
            "amounts": [6.0, 6.0],
            "amount_units": [str(amount_unit.id), str(amount_unit.id)],
        }
        refused = client.post("/aliquots/pool", json=body, headers=auth_headers)
        assert refused.status_code == 400, refused.text
        assert refused.json()["detail"]["code"] == "insufficient_amount"
        db_session.expire_all()
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == rich["source"].id).one().amount
        ) == Decimal("10")
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == poor["source"].id).one().amount
        ) == Decimal("3")
        assert db_session.query(Contents).filter(Contents.container_id == dest.id).count() == 0

        zero_conc = dict(body, amounts=[1.0, 1.0], concentrations=[0.0, 1.0])
        zero = client.post("/aliquots/pool", json=zero_conc, headers=auth_headers)
        assert zero.status_code == 400, zero.text
        assert "concentration is zero" in zero.text
        db_session.expire_all()
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == rich["source"].id).one().amount
        ) == Decimal("10")

    def test_pool_seed_like_concentration_units(self, db_session, auth_headers, sample_user):
        """Multiplier-1 units of one type are one scale. A different type is not.

        g/L and mg/mL are both multiplier 1 because 1 mg/mL = 1 g/L. EU/mL is
        activity, a different unit type, and must not convert onto that scale.
        """
        from app.core.conversions import canonical_base_unit
        from models.unit import Unit

        left = _tracked_parent(db_session, sample_user, label="seedpool-a", amount="50")
        right = _tracked_parent(db_session, sample_user, label="seedpool-b", amount="50")
        volume_type = get_or_create_list_entry(db_session, "unit_type", "volume")
        conc_type = scratch_entry_id(db_session)
        amount_unit = (
            db_session.query(Unit)
            .filter(Unit.type == volume_type.id, Unit.multiplier == 1, Unit.active == True)  # noqa: E712
            .first()
        )
        if amount_unit is None:
            amount_unit = Unit(
                name=f"mL_{uuid4().hex[:4]}",
                description="mL",
                type=volume_type.id,
                multiplier=1.0,
            )
            db_session.add(amount_unit)
        created = []
        for name in ("ng/µL", "µg/mL", "EU/mL", "copies/µL", "g/L"):
            unit = Unit(
                name=f"{name} {uuid4().hex[:6]}",
                description=name,
                type=conc_type,
                multiplier=1.0,
                created_by=sample_user.id,
                modified_by=sample_user.id,
            )
            db_session.add(unit)
            created.append(unit)
        db_session.flush()
        ng_ul, _ug_ml, eu_ml, _copies, _g_l = created
        eu_ml.type = scratch_entry_id(db_session)
        db_session.flush()
        for lab, conc_unit in ((left, ng_ul), (right, ng_ul)):
            row = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
            row.amount_units = amount_unit.id
            row.concentration = Decimal("10")
            row.concentration_units = conc_unit.id
        db_session.flush()
        dest = Container(
            name=f"Seed pool {uuid4().hex[:6]}",
            description="dest",
            type_id=left["container_type"].id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(dest)
        db_session.flush()
        shared = {
            "container_id": str(dest.id),
            "samples": [str(left["parent"].id), str(right["parent"].id)],
            "amounts": [5.0, 10.0],
            "amount_units": [str(amount_unit.id), str(amount_unit.id)],
            "source_container_ids": [str(left["source"].id), str(right["source"].id)],
        }
        mixed = client.post(
            "/aliquots/pool",
            json={
                **shared,
                "concentrations": [10.0, 20.0],
                "concentration_units": [str(ng_ul.id), str(eu_ml.id)],
            },
            headers=auth_headers,
        )
        assert mixed.status_code == 400, mixed.text
        assert mixed.json()["detail"]["code"] == "incompatible_units"
        db_session.expire_all()
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == left["source"].id).one().amount
        ) == Decimal("50")
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == right["source"].id).one().amount
        ) == Decimal("50")
        assert db_session.query(Contents).filter(Contents.container_id == dest.id).count() == 0

        pooled = client.post(
            "/aliquots/pool",
            json={
                **shared,
                "concentrations": [10.0, 20.0],
                "concentration_units": [str(ng_ul.id), str(ng_ul.id)],
            },
            headers=auth_headers,
        )
        assert pooled.status_code == 200, pooled.text
        body = pooled.json()
        same_scale = [unit for unit in created if unit.type == conc_type]
        assert body["concentration_units"] == str(canonical_base_unit(same_scale).id)
        assert abs(body["average_concentration"] - 15.0) < 0.001
        db_session.expire_all()
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == left["source"].id).one().amount
        ) == Decimal("45")
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == right["source"].id).one().amount
        ) == Decimal("40")
        dest_rows = db_session.query(Contents).filter(Contents.container_id == dest.id).all()
        assert {row.sample_id for row in dest_rows} == {left["parent"].id, right["parent"].id}
        for row in dest_rows:
            assert abs(float(row.concentration) - 15.0) < 0.001
            assert row.concentration_units == canonical_base_unit(same_scale).id

    def test_pool_converts_equal_mass_concentrations(self, db_session, auth_headers, sample_user):
        """ng/µL and µg/mL are the same scale. EU/mL is not."""
        from models.unit import Unit

        left = _tracked_parent(db_session, sample_user, label="masspool-a", amount="50")
        right = _tracked_parent(db_session, sample_user, label="masspool-b", amount="50")
        volume_type = get_or_create_list_entry(db_session, "unit_type", "volume")
        conc_type = scratch_entry_id(db_session)
        activity_type = scratch_entry_id(db_session)
        amount_unit = Unit(
            name=f"mL_{uuid4().hex[:6]}",
            description="mL",
            type=volume_type.id,
            multiplier=1.0,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        g_per_l = Unit(
            name="g/L",
            description="g/L",
            type=conc_type,
            multiplier=1,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        mg_per_ml = Unit(
            name=f"mg/mL {uuid4().hex[:4]}",
            description="mg/mL",
            type=conc_type,
            multiplier=1,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        ng_ul = Unit(
            name=f"ng/µL {uuid4().hex[:4]}",
            description="ng/µL",
            type=conc_type,
            multiplier=Decimal("0.001"),
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        ug_ml = Unit(
            name=f"µg/mL {uuid4().hex[:4]}",
            description="µg/mL",
            type=conc_type,
            multiplier=Decimal("0.001"),
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        eu_ml = Unit(
            name=f"EU/mL {uuid4().hex[:4]}",
            description="EU/mL",
            type=activity_type,
            multiplier=1,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add_all([amount_unit, g_per_l, mg_per_ml, ng_ul, ug_ml, eu_ml])
        db_session.flush()
        for lab, conc_unit in ((left, ng_ul), (right, ug_ml)):
            row = db_session.query(Contents).filter(Contents.container_id == lab["source"].id).one()
            row.amount_units = amount_unit.id
            row.concentration_units = conc_unit.id
        dest = Container(
            name=f"Mass pool {uuid4().hex[:6]}",
            description="dest",
            type_id=left["container_type"].id,
            created_by=sample_user.id,
            modified_by=sample_user.id,
        )
        db_session.add(dest)
        db_session.flush()
        shared = {
            "container_id": str(dest.id),
            "samples": [str(left["parent"].id), str(right["parent"].id)],
            "amounts": [1.0, 1.0],
            "amount_units": [str(amount_unit.id), str(amount_unit.id)],
            "source_container_ids": [str(left["source"].id), str(right["source"].id)],
        }
        pooled = client.post(
            "/aliquots/pool",
            json={
                **shared,
                "concentrations": [1000.0, 1000.0],
                "concentration_units": [str(ng_ul.id), str(ug_ml.id)],
            },
            headers=auth_headers,
        )
        assert pooled.status_code == 200, pooled.text
        body = pooled.json()
        assert body["concentration_units"] == str(g_per_l.id)
        assert abs(body["average_concentration"] - 1.0) < 0.0001
        db_session.expire_all()
        mixed_rows = db_session.query(Contents).filter(Contents.container_id == dest.id).all()
        assert len(mixed_rows) == 2
        for row in mixed_rows:
            assert abs(float(row.concentration) - 1.0) < 0.0001
            assert row.concentration_units == g_per_l.id
            assert row.concentration != Decimal("1000")
        db_session.expire_all()
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == left["source"].id).one().amount
        ) == Decimal("49")

        refused = client.post(
            "/aliquots/pool",
            json={
                **shared,
                "container_id": str(dest.id),
                "concentrations": [1000.0, 5.0],
                "concentration_units": [str(ng_ul.id), str(eu_ml.id)],
            },
            headers=auth_headers,
        )
        assert refused.status_code == 400, refused.text
        assert refused.json()["detail"]["code"] == "incompatible_units"
        db_session.expire_all()
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == left["source"].id).one().amount
        ) == Decimal("49")
        assert Decimal(
            db_session.query(Contents).filter(Contents.container_id == right["source"].id).one().amount
        ) == Decimal("49")


def test_parallel_aliquots_do_not_overdraw(db_engine):
    """Concurrent draws of 6 from 10: one succeeds, the vessel is never negative."""
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from fastapi import HTTPException
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.database import _engine_kwargs
    from app.routers.aliquots import create_aliquot
    from app.schemas.aliquot import AliquotCreateRequest
    from models.client import Client
    from models.list import List, ListEntry
    from models.project import Project
    from models.user import Role

    parallel = 8
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, pool_size=5, max_overflow=10, **_engine_kwargs(url))
    session_factory = sessionmaker(bind=engine, autoflush=False)
    tag = uuid4().hex[:8]
    ids = {}
    with session_factory() as session:
        org = Client(name=f"ALQ race {tag}", description="race", billing_info={})
        role = Role(name=f"alq-race-{tag}", description="race")
        session.add_all([org, role])
        session.flush()
        user = User(
            name=f"ALQ race {tag}",
            username=f"alqrace{tag}",
            email=f"alqrace{tag}@example.com",
            password_hash="x",
            role_id=role.id,
            client_id=org.id,
            must_change_password=False,
        )
        session.add(user)
        session.flush()
        status_list = List(name=f"alq-status-{tag}", description="status")
        type_list = List(name=f"alq-type-{tag}", description="type")
        session.add_all([status_list, type_list])
        session.flush()
        status_entry = ListEntry(
            list_id=status_list.id, name=f"Available {tag}", description="status",
            created_by=user.id, modified_by=user.id,
        )
        type_entry = ListEntry(
            list_id=type_list.id, name=f"Blood {tag}", description="Blood",
            created_by=user.id, modified_by=user.id,
        )
        matrix_entry = ListEntry(
            list_id=type_list.id, name=f"Matrix {tag}", description="matrix",
            created_by=user.id, modified_by=user.id,
        )
        project_status = ListEntry(
            list_id=status_list.id, name=f"Open {tag}", description="open",
            created_by=user.id, modified_by=user.id,
        )
        session.add_all([status_entry, type_entry, matrix_entry, project_status])
        session.flush()
        project = Project(
            name=f"ALQ race project {tag}",
            description="race",
            start_date="2024-01-01",
            client_id=org.id,
            status=project_status.id,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(project)
        session.flush()
        parent = Sample(
            name=f"ALQ race parent {tag}",
            description="race",
            sample_type=type_entry.id,
            status=status_entry.id,
            matrix=matrix_entry.id,
            project_id=project.id,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(parent)
        session.flush()
        ctype = ContainerType(
            name=f"ALQ race tube {tag}",
            description="tube",
            rows=1,
            columns=1,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(ctype)
        session.flush()
        source = Container(
            name=f"ALQ race source {tag}",
            description="source",
            type_id=ctype.id,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(source)
        session.flush()
        session.add(Contents(container_id=source.id, sample_id=parent.id, amount=Decimal("10")))
        dests = []
        for index in range(parallel):
            dest = Container(
                name=f"ALQ race dest {tag}-{index}",
                description="dest",
                type_id=ctype.id,
                created_by=user.id,
                modified_by=user.id,
            )
            dests.append(dest)
        session.add_all(dests)
        session.commit()
        ids = {
            "user": user.id,
            "sample": parent.id,
            "source": source.id,
            "dests": [dest.id for dest in dests],
            "org": org.id,
            "role": role.id,
            "project": project.id,
            "ctype": ctype.id,
            "lists": [status_list.id, type_list.id],
            "entries": [status_entry.id, type_entry.id, matrix_entry.id, project_status.id],
        }

    def _draw(dest_id):
        gate.wait()
        with session_factory() as session:
            user = session.get(User, ids["user"])
            try:
                create_aliquot(
                    AliquotCreateRequest(
                        parent_sample_id=ids["sample"],
                        container_id=dest_id,
                        source_container_id=ids["source"],
                        amount=6,
                    ),
                    current_user=user,
                    db=session,
                )
                return 200, None
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
                return exc.status_code, detail.get("code")
            except Exception as exc:  # surface unexpected failures in the assertion
                return type(exc).__name__, str(exc)

    gate = threading.Barrier(parallel)
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(parallel) as pool:
            codes = list(pool.map(_draw, ids["dests"]))
        elapsed = time.monotonic() - started
        assert elapsed < 20, elapsed
        assert codes.count((200, None)) == 1, codes
        assert {code for code, _ in codes if code != 200} == {400}, codes
        assert all(detail == "insufficient_amount" for code, detail in codes if code == 400)
        with session_factory() as session:
            left = session.query(Contents).filter(Contents.container_id == ids["source"]).one()
            placements = session.query(Contents).filter(Contents.sample_id == ids["sample"]).count()
            children = session.query(Sample).filter(Sample.parent_sample_id == ids["sample"]).count()
            parent = session.get(Sample, ids["sample"])
            idle = session.execute(text(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction' "
                "AND pid <> pg_backend_pid()"
            )).scalar()
        assert Decimal(left.amount) == Decimal("4")
        assert placements == 2
        assert children == 0
        assert parent.active is True
        assert idle == 0
    finally:
        if ids:
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM contents WHERE sample_id = :i"), {"i": ids["sample"]})
                connection.execute(
                    text("DELETE FROM samples WHERE id = :i OR parent_sample_id = :i"),
                    {"i": ids["sample"]},
                )
                connection.execute(text("DELETE FROM containers WHERE type_id = :i"), {"i": ids["ctype"]})
                connection.execute(text("DELETE FROM container_types WHERE id = :i"), {"i": ids["ctype"]})
                connection.execute(text("DELETE FROM projects WHERE id = :i"), {"i": ids["project"]})
                for entry_id in ids["entries"]:
                    connection.execute(text("DELETE FROM list_entries WHERE id = :i"), {"i": entry_id})
                for list_id in ids["lists"]:
                    connection.execute(text("DELETE FROM lists WHERE id = :i"), {"i": list_id})
                connection.execute(text("DELETE FROM users WHERE id = :i"), {"i": ids["user"]})
                connection.execute(text("DELETE FROM roles WHERE id = :i"), {"i": ids["role"]})
                connection.execute(text("DELETE FROM clients WHERE id = :i"), {"i": ids["org"]})
        engine.dispose()


def test_parallel_pools_do_not_overdraw(db_engine):
    """Two sources of 10. Concurrent pools each draw 6 from both. One pool wins."""
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from fastapi import HTTPException
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.database import _engine_kwargs
    from app.routers.aliquots import pool_samples
    from app.schemas.aliquot import PoolingRequest
    from models.client import Client
    from models.list import List, ListEntry
    from models.project import Project
    from models.unit import Unit
    from models.user import Role

    parallel = 8
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, pool_size=5, max_overflow=10, **_engine_kwargs(url))
    session_factory = sessionmaker(bind=engine, autoflush=False)
    tag = uuid4().hex[:8]
    ids: dict = {}
    with session_factory() as session:
        org = Client(name=f"POOL race {tag}", description="race", billing_info={})
        role = Role(name=f"pool-race-{tag}", description="race")
        session.add_all([org, role])
        session.flush()
        user = User(
            name=f"POOL race {tag}",
            username=f"poolrace{tag}",
            email=f"poolrace{tag}@example.com",
            password_hash="x",
            role_id=role.id,
            client_id=org.id,
            must_change_password=False,
        )
        session.add(user)
        session.flush()
        status_list = List(name=f"pool-status-{tag}", description="status")
        type_list = List(name=f"pool-type-{tag}", description="type")
        session.add_all([status_list, type_list])
        session.flush()
        status_entry = ListEntry(
            list_id=status_list.id, name=f"Available {tag}", description="status",
            created_by=user.id, modified_by=user.id,
        )
        type_entry = ListEntry(
            list_id=type_list.id, name=f"Blood {tag}", description="Blood",
            created_by=user.id, modified_by=user.id,
        )
        matrix_entry = ListEntry(
            list_id=type_list.id, name=f"Matrix {tag}", description="matrix",
            created_by=user.id, modified_by=user.id,
        )
        project_status = ListEntry(
            list_id=status_list.id, name=f"Open {tag}", description="open",
            created_by=user.id, modified_by=user.id,
        )
        conc_type = ListEntry(
            list_id=type_list.id, name=f"conc {tag}", description="concentration",
            created_by=user.id, modified_by=user.id,
        )
        session.add_all([status_entry, type_entry, matrix_entry, project_status, conc_type])
        session.flush()
        volume_entry = (
            session.query(ListEntry).filter(ListEntry.name == "volume").first()
        )
        own_volume = volume_entry is None
        if volume_entry is None:
            volume_entry = ListEntry(
                list_id=type_list.id, name="volume", description="volume",
                created_by=user.id, modified_by=user.id,
            )
            session.add(volume_entry)
            session.flush()
        amount_unit = (
            session.query(Unit)
            .filter(Unit.type == volume_entry.id, Unit.multiplier == 1, Unit.active == True)  # noqa: E712
            .first()
        )
        own_amount_unit = amount_unit is None
        if amount_unit is None:
            amount_unit = Unit(
                name=f"mL_{tag}", description="mL", type=volume_entry.id, multiplier=1,
            )
            session.add(amount_unit)
        conc_unit = Unit(
            name=f"mgmL_{tag}", description="mg/mL", type=conc_type.id, multiplier=1,
        )
        session.add(conc_unit)
        session.flush()
        project = Project(
            name=f"POOL race project {tag}",
            description="race",
            start_date="2024-01-01",
            client_id=org.id,
            status=project_status.id,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(project)
        session.flush()
        samples = []
        sources = []
        for index in range(2):
            sample = Sample(
                name=f"POOL race sample {tag}-{index}",
                description="race",
                sample_type=type_entry.id,
                status=status_entry.id,
                matrix=matrix_entry.id,
                project_id=project.id,
                created_by=user.id,
                modified_by=user.id,
            )
            session.add(sample)
            session.flush()
            samples.append(sample)
        ctype = ContainerType(
            name=f"POOL race tube {tag}",
            description="tube",
            rows=1,
            columns=1,
            created_by=user.id,
            modified_by=user.id,
        )
        session.add(ctype)
        session.flush()
        for index, sample in enumerate(samples):
            source = Container(
                name=f"POOL race source {tag}-{index}",
                description="source",
                type_id=ctype.id,
                created_by=user.id,
                modified_by=user.id,
            )
            session.add(source)
            session.flush()
            session.add(Contents(container_id=source.id, sample_id=sample.id, amount=Decimal("10")))
            sources.append(source)
        dests = []
        for index in range(parallel):
            dest = Container(
                name=f"POOL race dest {tag}-{index}",
                description="dest",
                type_id=ctype.id,
                created_by=user.id,
                modified_by=user.id,
            )
            dests.append(dest)
        session.add_all(dests)
        session.commit()
        ids = {
            "user": user.id,
            "samples": [sample.id for sample in samples],
            "sources": [source.id for source in sources],
            "dests": [dest.id for dest in dests],
            "org": org.id,
            "role": role.id,
            "project": project.id,
            "ctype": ctype.id,
            "lists": [status_list.id, type_list.id],
            "entries": [
                status_entry.id, type_entry.id, matrix_entry.id, project_status.id, conc_type.id,
            ],
            "units": [conc_unit.id] + ([amount_unit.id] if own_amount_unit else []),
            "amount_unit": amount_unit.id,
            "conc_unit": conc_unit.id,
        }
        if own_volume:
            ids["entries"].append(volume_entry.id)

    def _draw(dest_id):
        gate.wait()
        with session_factory() as session:
            user = session.get(User, ids["user"])
            try:
                pool_samples(
                    PoolingRequest(
                        container_id=dest_id,
                        samples=ids["samples"],
                        concentrations=[1, 1],
                        concentration_units=[ids["conc_unit"], ids["conc_unit"]],
                        amounts=[6, 6],
                        amount_units=[ids["amount_unit"], ids["amount_unit"]],
                        source_container_ids=ids["sources"],
                    ),
                    current_user=user,
                    db=session,
                )
                return 200, None
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
                return exc.status_code, detail.get("code") or detail.get("message")
            except Exception as exc:
                return type(exc).__name__, str(exc)

    gate = threading.Barrier(parallel)
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(parallel) as pool:
            codes = list(pool.map(_draw, ids["dests"]))
        elapsed = time.monotonic() - started
        assert elapsed < 20, elapsed
        assert codes.count((200, None)) == 1, codes
        assert {code for code, _ in codes if code != 200} == {400}, codes
        assert all(detail == "insufficient_amount" for _code, detail in codes if _code == 400), codes
        with session_factory() as session:
            for source_id in ids["sources"]:
                left = session.query(Contents).filter(Contents.container_id == source_id).one()
                assert Decimal(left.amount) == Decimal("4")
            placed = session.query(Contents).filter(Contents.sample_id.in_(ids["samples"])).count()
            children = session.query(Sample).filter(
                Sample.parent_sample_id.in_(ids["samples"])
            ).count()
            idle = session.execute(text(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction' "
                "AND pid <> pg_backend_pid()"
            )).scalar()
        assert placed == 4
        assert children == 0
        assert idle == 0
    finally:
        if ids:
            with engine.begin() as connection:
                for sample_id in ids["samples"]:
                    connection.execute(
                        text("DELETE FROM contents WHERE sample_id = :i"), {"i": sample_id}
                    )
                    connection.execute(
                        text("DELETE FROM samples WHERE id = :i OR parent_sample_id = :i"),
                        {"i": sample_id},
                    )
                connection.execute(text("DELETE FROM containers WHERE type_id = :i"), {"i": ids["ctype"]})
                connection.execute(text("DELETE FROM container_types WHERE id = :i"), {"i": ids["ctype"]})
                for unit_id in ids["units"]:
                    connection.execute(text("DELETE FROM units WHERE id = :i"), {"i": unit_id})
                connection.execute(text("DELETE FROM projects WHERE id = :i"), {"i": ids["project"]})
                for entry_id in ids["entries"]:
                    connection.execute(text("DELETE FROM list_entries WHERE id = :i"), {"i": entry_id})
                for list_id in ids["lists"]:
                    connection.execute(text("DELETE FROM lists WHERE id = :i"), {"i": list_id})
                connection.execute(text("DELETE FROM users WHERE id = :i"), {"i": ids["user"]})
                connection.execute(text("DELETE FROM roles WHERE id = :i"), {"i": ids["role"]})
                connection.execute(text("DELETE FROM clients WHERE id = :i"), {"i": ids["org"]})
        engine.dispose()
