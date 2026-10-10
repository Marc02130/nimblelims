"""
Integration tests for EAV expansion to results, projects, client_projects, and batches
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.custom_attributes_config import CustomAttributeConfig
from models.result import Result
from models.project import Project
from models.client import ClientProject
from models.batch import Batch
from models.user import User, Role, Permission
from app.core.security import create_access_token
from datetime import datetime
from uuid import uuid4
import json


@pytest.fixture
def test_data(db_session: Session, test_admin_user, test_org):
    """Minimal graph these tests need (they used to rely on pre-seeded rows and
    skip when absent): project, sample, analysis/analyte, test, batch_status."""
    from datetime import timedelta
    from models.analysis import Analysis, Analyte, AnalysisAnalyte
    from models.sample import Sample
    from models.test import Test
    from tests._fk_helpers import get_or_create_list_entry, scratch_entry_id

    project = Project(
        name=f"EAV Project {uuid4().hex[:6]}",
        client_id=test_org.id,
        status=get_or_create_list_entry(db_session, "project_status", "Active").id,
        start_date=datetime.utcnow(),
    )
    db_session.add(project)
    db_session.flush()
    sample = Sample(
        name=f"EAV-S-{uuid4().hex[:6]}",
        sample_type=scratch_entry_id(db_session),
        status=scratch_entry_id(db_session),
        matrix=scratch_entry_id(db_session),
        project_id=project.id,
        due_date=datetime.utcnow() + timedelta(days=7),
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    analysis = Analysis(name=f"EAV-A-{uuid4().hex[:6]}", created_by=test_admin_user.id, modified_by=test_admin_user.id)
    analyte = Analyte(name=f"EAV-An-{uuid4().hex[:6]}", created_by=test_admin_user.id, modified_by=test_admin_user.id)
    db_session.add_all([sample, analysis, analyte])
    db_session.flush()
    db_session.add(AnalysisAnalyte(analysis_id=analysis.id, analyte_id=analyte.id))
    test = Test(
        name=f"EAV-T-{uuid4().hex[:6]}",
        sample_id=sample.id,
        analysis_id=analysis.id,
        status=get_or_create_list_entry(db_session, "test_status", "In Process").id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(test)
    get_or_create_list_entry(db_session, "batch_status", "Created")
    db_session.commit()
    return {"analyte_id": analyte.id, "user_id": test_admin_user.id, "test_id": test.id}


class TestEAVExpansion:
    """Test EAV support for results, projects, client_projects, and batches"""

    @pytest.fixture
    def admin_token(self, client: TestClient, test_admin_user: User):
        # sub must be the user id (not username) and tokens carry password_epoch;
        # log in through the API instead of minting a token by hand.
        r = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    @pytest.fixture
    def setup_custom_attributes(self, client: TestClient, db_session: Session, admin_token: str):
        """Setup custom attribute configs for all entity types"""
        configs = {}
        
        # Results config
        response = client.post(
            "/admin/custom-attributes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "entity_type": "results",
                "attr_name": "reviewer_notes",
                "data_type": "text",
                "validation_rules": {"max_length": 500},
                "description": "Reviewer notes for result"
            }
        )
        assert response.status_code == 201, response.text
        configs['results'] = response.json()
        
        # Projects config
        response = client.post(
            "/admin/custom-attributes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "entity_type": "projects",
                "attr_name": "budget_code",
                "data_type": "text",
                "validation_rules": {"max_length": 50},
                "description": "Budget code for project"
            }
        )
        assert response.status_code == 201, response.text
        configs['projects'] = response.json()
        
        # Client projects config
        response = client.post(
            "/admin/custom-attributes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "entity_type": "client_projects",
                "attr_name": "contract_number",
                "data_type": "text",
                "validation_rules": {"max_length": 100},
                "description": "Contract number for client project"
            }
        )
        assert response.status_code == 201, response.text
        configs['client_projects'] = response.json()
        
        # Batches config
        response = client.post(
            "/admin/custom-attributes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "entity_type": "batches",
                "attr_name": "instrument_serial",
                "data_type": "text",
                "validation_rules": {"max_length": 50},
                "description": "Instrument serial number used for batch"
            }
        )
        assert response.status_code == 201, response.text
        configs['batches'] = response.json()
        
        db_session.commit()
        return configs

    def test_result_custom_attributes_validation(self, client: TestClient, db_session: Session, 
                                                  admin_token: str, setup_custom_attributes, 
                                                  test_data):
        """Test that results validate custom_attributes correctly"""
        # Create a test first
        from models.test import Test
        from models.sample import Sample
        
        sample = db_session.query(Sample).first()
        if not sample:
            pytest.skip("No sample found in test data")
        
        test = db_session.query(Test).filter(Test.sample_id == sample.id).first()
        if not test:
            pytest.skip("No test found in test data")
        
        # Create result with valid custom_attributes
        response = client.post(
            "/results/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "test_id": str(test.id),
                "analyte_id": str(test_data['analyte_id']),
                "raw_result": "10.5",
                "reported_result": "10.5",
                "entered_by": str(test_data['user_id']),
                "custom_attributes": {
                    "reviewer_notes": "Looks good"
                }
            }
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["custom_attributes"]["reviewer_notes"] == "Looks good"
        
        # Try with invalid custom attribute (too long)
        response = client.post(
            "/results/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "test_id": str(test.id),
                "analyte_id": str(test_data['analyte_id']),
                "raw_result": "10.5",
                "reported_result": "10.5",
                "entered_by": str(test_data['user_id']),
                "custom_attributes": {
                    "reviewer_notes": "x" * 501  # Exceeds max_length
                }
            }
        )
        assert response.status_code == 400, response.text

    def test_project_custom_attributes(self, client: TestClient, db_session: Session,
                                       admin_token: str, setup_custom_attributes, test_data):
        """Test that projects can have custom_attributes"""
        # Note: Projects router is read-only, so we test via direct model access
        project = db_session.query(Project).first()
        if not project:
            pytest.skip("No project found in test data")
        
        # Update project directly with custom_attributes
        project.custom_attributes = {"budget_code": "BUDGET-001"}
        db_session.commit()
        db_session.refresh(project)
        
        assert project.custom_attributes["budget_code"] == "BUDGET-001"

    def test_client_project_custom_attributes(self, client: TestClient, db_session: Session,
                                             admin_token: str, setup_custom_attributes, test_data):
        """Test that client_projects validate and store custom_attributes"""
        from models.client import Client
        
        client_obj = db_session.query(Client).first()
        if not client_obj:
            pytest.skip("No client found in test data")
        
        # Create client project with custom_attributes
        response = client.post(
            "/client-projects",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"Test Project {uuid4()}",
                "description": "Test project",
                "client_id": str(client_obj.id),
                "custom_attributes": {
                    "contract_number": "CONTRACT-123"
                }
            }
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["custom_attributes"]["contract_number"] == "CONTRACT-123"
        
        # Update with invalid custom attribute
        response = client.patch(
            f"/client-projects/{data['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "custom_attributes": {
                    "contract_number": "x" * 101  # Exceeds max_length
                }
            }
        )
        assert response.status_code == 400, response.text

    def test_batch_custom_attributes(self, client: TestClient, db_session: Session,
                                     admin_token: str, setup_custom_attributes, test_data):
        """Test that batches validate and store custom_attributes"""
        from models.list import ListEntry
        
        # Get batch status
        status = db_session.query(ListEntry).filter(
            ListEntry.list.has(name="batch_status")
        ).first()
        if not status:
            pytest.skip("No batch status found in test data")
        
        # Create batch with custom_attributes
        response = client.post(
            "/batches",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"Test Batch {uuid4()}",
                "description": "Test batch",
                "status": str(status.id),
                "custom_attributes": {
                    "instrument_serial": "INST-12345"
                }
            }
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["custom_attributes"]["instrument_serial"] == "INST-12345"
        
        # Update batch with custom_attributes
        response = client.patch(
            f"/batches/{data['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "custom_attributes": {
                    "instrument_serial": "INST-67890"
                }
            }
        )
        assert response.status_code == 200, response.text
        updated_data = response.json()
        assert updated_data["custom_attributes"]["instrument_serial"] == "INST-67890"

    def test_cross_entity_custom_attributes_querying(self, client: TestClient, db_session: Session,
                                                     admin_token: str, setup_custom_attributes, test_data):
        """Test querying entities by custom_attributes across different entity types"""
        from models.test import Test
        from models.sample import Sample
        
        # Create results with different custom_attributes
        sample = db_session.query(Sample).first()
        if not sample:
            pytest.skip("No sample found")
        
        test = db_session.query(Test).filter(Test.sample_id == sample.id).first()
        if not test:
            pytest.skip("No test found")
        
        # Create multiple results with different reviewer_notes
        for i in range(3):
            response = client.post(
                "/results/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "test_id": str(test.id),
                    "analyte_id": str(test_data['analyte_id']),
                    "raw_result": f"{10.5 + i}",
                    "reported_result": f"{10.5 + i}",
                    "entered_by": str(test_data['user_id']),
                    "custom_attributes": {
                        "reviewer_notes": f"Note {i}"
                    }
                }
            )
            assert response.status_code == 200, response.text
        
        # Query results by custom attribute
        response = client.get(
            "/results/",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"custom.reviewer_notes": "Note 1"}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["results"]) >= 1
        assert all(r["custom_attributes"]["reviewer_notes"] == "Note 1" for r in data["results"])

    def test_custom_attributes_inactive_config(self, client: TestClient, db_session: Session,
                                              admin_token: str, setup_custom_attributes, test_data):
        """Test that inactive custom attribute configs are not accepted"""
        from models.test import Test
        from models.sample import Sample
        
        # Deactivate a config
        config_id = setup_custom_attributes['results']['id']
        response = client.patch(
            f"/admin/custom-attributes/{config_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"active": False}
        )
        assert response.status_code == 200, response.text
        
        # Try to use the inactive config
        sample = db_session.query(Sample).first()
        if not sample:
            pytest.skip("No sample found")
        
        test = db_session.query(Test).filter(Test.sample_id == sample.id).first()
        if not test:
            pytest.skip("No test found")
        
        response = client.post(
            "/results/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "test_id": str(test.id),
                "analyte_id": str(test_data['analyte_id']),
                "raw_result": "10.5",
                "reported_result": "10.5",
                "entered_by": str(test_data['user_id']),
                "custom_attributes": {
                    "reviewer_notes": "Should fail"
                }
            }
        )
        assert response.status_code == 400, response.text
        # detail is now structured: {"message": ..., "errors": [...]}
        assert "Unknown custom attribute" in str(response.json()["detail"])

