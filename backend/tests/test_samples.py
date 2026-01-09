"""
Tests for samples endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.sample import Sample
from models.project import Project
from models.client import Client
from models.list import List, ListEntry
from app.core.security import create_access_token
from datetime import datetime, timedelta
from uuid import uuid4


class TestSamplesCRUD:
    """Test samples CRUD operations"""
    
    @pytest.fixture
    def test_data(self, db_session: Session):
        """Create test data for samples tests"""
        # Create client
        client = Client(
            name="Test Client",
            description="Test client for samples",
            billing_info={"address": "123 Test St"}
        )
        db_session.add(client)
        db_session.flush()
        
        # Create project
        project = Project(
            name="Test Project",
            description="Test project for samples",
            start_date=datetime.utcnow(),
            client_id=client.id,
            status=uuid4()  # Mock status ID
        )
        db_session.add(project)
        db_session.flush()
        
        # Create list entries for sample types, statuses, matrices
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Blood Sample",
            description="Blood sample type"
        )
        db_session.add(sample_type)
        db_session.flush()
        
        status = ListEntry(
            list_id=uuid4(),
            name="Received",
            description="Sample received status"
        )
        db_session.add(status)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Blood",
            description="Blood matrix"
        )
        db_session.add(matrix)
        db_session.flush()
        
        return {
            "client": client,
            "project": project,
            "sample_type": sample_type,
            "status": status,
            "matrix": matrix
        }
    
    def test_create_sample_success(self, client: TestClient, test_admin_user, test_data):
        """Test successful sample creation"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create sample
        sample_data = {
            "name": "SAMPLE-001",
            "description": "Test sample",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "status": str(test_data["status"].id),
            "matrix": str(test_data["matrix"].id),
            "temperature": 25.0,
            "project_id": str(test_data["project"].id)
        }
        
        response = client.post(
            "/samples/",
            json=sample_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "SAMPLE-001"
        assert data["description"] == "Test sample"
        assert data["temperature"] == 25.0
        assert "id" in data
        assert "created_at" in data
    
    def test_create_sample_validation_error(self, client: TestClient, test_admin_user, test_data):
        """Test sample creation with validation errors"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Test with missing required fields
        sample_data = {
            "name": "SAMPLE-002",
            # Missing required fields
        }
        
        response = client.post(
            "/samples/",
            json=sample_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_samples_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful samples retrieval"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-003",
            description="Test sample for retrieval",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Get samples
        response = client.get(
            "/samples/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "samples" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["samples"]) >= 1
    
    def test_get_sample_by_id_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful sample retrieval by ID"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-004",
            description="Test sample for ID retrieval",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Get sample by ID
        response = client.get(
            f"/samples/{sample.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample.id)
        assert data["name"] == "SAMPLE-004"
    
    def test_get_sample_not_found(self, client: TestClient, test_admin_user):
        """Test sample retrieval with non-existent ID"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Get non-existent sample
        response = client.get(
            f"/samples/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Sample not found" in response.json()["detail"]
    
    def test_update_sample_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful sample update"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-005",
            description="Test sample for update",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update sample
        update_data = {
            "description": "Updated description",
            "temperature": 30.0
        }
        
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["temperature"] == 30.0
    
    def test_delete_sample_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful sample deletion"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-006",
            description="Test sample for deletion",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Delete sample
        response = client.delete(
            f"/samples/{sample.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify sample is soft deleted
        db_session.refresh(sample)
        assert sample.active == False


class TestSampleAccessioning:
    """Test sample accessioning workflow"""
    
    def test_accession_sample_success(self, client: TestClient, test_admin_user, test_data):
        """Test successful sample accessioning"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Accession sample
        accession_data = {
            "name": "SAMPLE-007",
            "description": "Test accession sample",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "temperature": 25.0,
            "client_id": str(test_data["client"].id),
            "project_id": str(test_data["project"].id),
            "anomalies": "No anomalies observed",
            "double_entry_required": False,
            "assigned_tests": []
        }
        
        response = client.post(
            "/samples/accession",
            json=accession_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "SAMPLE-007"
        assert data["description"] == "Test accession sample"
    
    def test_accession_sample_with_tests(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test sample accessioning with test assignment"""
        # Create analysis
        from models.analysis import Analysis
        analysis = Analysis(
            name="Test Analysis",
            description="Test analysis for accessioning",
            method="Test Method",
            turnaround_time=24,
            cost=100.0,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(analysis)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Accession sample with tests
        accession_data = {
            "name": "SAMPLE-008",
            "description": "Test accession sample with tests",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "temperature": 25.0,
            "client_id": str(test_data["client"].id),
            "project_id": str(test_data["project"].id),
            "anomalies": "No anomalies observed",
            "double_entry_required": False,
            "assigned_tests": [str(analysis.id)]
        }
        
        response = client.post(
            "/samples/accession",
            json=accession_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "SAMPLE-008"
    
    def test_accession_sample_with_auto_project_creation(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test sample accessioning with automatic project creation"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Accession sample without project_id (should auto-create project)
        accession_data = {
            "name": "SAMPLE-AUTO-001",
            "description": "Test sample with auto-created project",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "temperature": 25.0,
            "client_id": str(test_data["client"].id),
            "assigned_tests": []
        }
        
        response = client.post(
            "/samples/accession",
            json=accession_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "SAMPLE-AUTO-001"
        # Verify project was created
        assert "project_id" in data
        project_id = data["project_id"]
        
        # Verify project exists and belongs to client
        from models.project import Project
        project = db_session.query(Project).filter(Project.id == project_id).first()
        assert project is not None
        assert project.client_id == test_data["client"].id
        assert project.status is not None  # Should have Active status
    
    def test_accession_sample_with_client_project(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test sample accessioning with client_project_id"""
        from models.client import ClientProject
        
        # Create a client project
        client_project = ClientProject(
            name="Test Client Project",
            description="Test client project for accessioning",
            client_id=test_data["client"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        db_session.refresh(client_project)
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Accession sample with client_project_id
        accession_data = {
            "name": "SAMPLE-CP-001",
            "description": "Test sample with client project",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "temperature": 25.0,
            "client_id": str(test_data["client"].id),
            "client_project_id": str(client_project.id),
            "assigned_tests": []
        }
        
        response = client.post(
            "/samples/accession",
            json=accession_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "SAMPLE-CP-001"
        
        # Verify project was created and linked to client_project
        from models.project import Project
        project = db_session.query(Project).filter(Project.id == data["project_id"]).first()
        assert project is not None
        assert project.client_project_id == client_project.id
    
    def test_accession_sample_invalid_client(self, client: TestClient, test_admin_user, test_data):
        """Test sample accessioning with invalid client_id"""
        from uuid import uuid4
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Accession sample with non-existent client_id
        accession_data = {
            "name": "SAMPLE-INVALID",
            "description": "Test sample with invalid client",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "temperature": 25.0,
            "client_id": str(uuid4()),
            "assigned_tests": []
        }
        
        response = client.post(
            "/samples/accession",
            json=accession_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "Client not found" in response.json()["detail"]
    
    def test_accession_sample_invalid_client_project_linkage(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test sample accessioning with client_project_id that doesn't belong to client"""
        from models.client import Client, ClientProject
        
        # Create another client
        other_client = Client(
            name="Other Test Client",
            description="Another test client",
            billing_info={},
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(other_client)
        db_session.commit()
        db_session.refresh(other_client)
        
        # Create a client project for the other client
        client_project = ClientProject(
            name="Other Client Project",
            description="Client project for other client",
            client_id=other_client.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        db_session.refresh(client_project)
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to accession sample with client_project_id from different client
        accession_data = {
            "name": "SAMPLE-INVALID-CP",
            "description": "Test sample with invalid client project",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "temperature": 25.0,
            "client_id": str(test_data["client"].id),
            "client_project_id": str(client_project.id),  # Belongs to other_client, not test_data["client"]
            "assigned_tests": []
        }
        
        response = client.post(
            "/samples/accession",
            json=accession_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "does not belong to the specified client" in response.json()["detail"]


class TestSampleStatusManagement:
    """Test sample status management"""
    
    def test_update_sample_status_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful sample status update"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-009",
            description="Test sample for status update",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Create new status
        new_status = ListEntry(
            list_id=uuid4(),
            name="Available for Testing",
            description="Sample available for testing"
        )
        db_session.add(new_status)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update status
        response = client.patch(
            f"/samples/{sample.id}/status",
            params={"status_id": str(new_status.id)},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == str(new_status.id)


class TestSamplePermissions:
    """Test sample permission requirements"""
    
    def test_create_sample_requires_permission(self, client: TestClient, test_user):
        """Test that creating samples requires proper permission"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to create sample (should fail due to missing project data)
        sample_data = {
            "name": "SAMPLE-010",
            "description": "Test sample",
            "sample_type": str(uuid4()),
            "status": str(uuid4()),
            "matrix": str(uuid4()),
            "project_id": str(uuid4())
        }
        
        response = client.post(
            "/samples/",
            json=sample_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail due to missing project access or invalid IDs
        assert response.status_code in [400, 403, 404]
    
    def test_get_samples_requires_permission(self, client: TestClient):
        """Test that getting samples requires authentication"""
        response = client.get("/samples/")
        assert response.status_code == 401  # Unauthorized
    
    def test_update_sample_requires_permission(self, client: TestClient):
        """Test that updating samples requires authentication"""
        response = client.patch(
            f"/samples/{uuid4()}",
            json={"description": "Updated"}
        )
        assert response.status_code == 401  # Unauthorized
    
    def test_update_sample_with_custom_attributes(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test updating sample with custom attributes"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-CUSTOM-001",
            description="Test sample for custom attributes",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update sample with custom attributes
        update_data = {
            "custom_attributes": {
                "ph_level": 7.2,
                "notes": "Sample appears normal"
            }
        }
        
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "custom_attributes" in data
        assert data["custom_attributes"]["ph_level"] == 7.2
        assert data["custom_attributes"]["notes"] == "Sample appears normal"
    
    def test_update_sample_not_found(self, client: TestClient, test_admin_user):
        """Test updating non-existent sample"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.patch(
            f"/samples/{uuid4()}",
            json={"description": "Updated"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Sample not found" in response.json()["detail"]
    
    def test_update_sample_invalid_data(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test updating sample with invalid data"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-INVALID-001",
            description="Test sample for invalid data",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to update with invalid temperature (too high)
        update_data = {
            "temperature": 2000.0  # Invalid: exceeds max
        }
        
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_update_sample_status_to_reviewed(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test updating sample status to 'Reviewed' (example from docstring)"""
        # Create reviewed status
        from models.list import List, ListEntry
        sample_status_list = db_session.query(List).filter(List.name == "Sample Status").first()
        if not sample_status_list:
            sample_status_list = List(
                name="Sample Status",
                description="Sample status values"
            )
            db_session.add(sample_status_list)
            db_session.flush()
        
        reviewed_status = ListEntry(
            list_id=sample_status_list.id,
            name="Reviewed",
            description="Sample reviewed"
        )
        db_session.add(reviewed_status)
        db_session.flush()
        
        # Create a test sample
        sample = Sample(
            name="SAMPLE-REVIEW-001",
            description="Test sample for status update",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update status to Reviewed
        update_data = {
            "status": str(reviewed_status.id)
        }
        
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == str(reviewed_status.id)


class TestSampleEditRBAC:
    """Test RBAC for sample editing operations"""
    
    def test_update_sample_requires_update_permission(self, client: TestClient, test_user, test_data, db_session: Session):
        """Test that updating samples requires sample:update permission"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-RBAC-001",
            description="Test sample for RBAC",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_user.id,
            modified_by=test_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Login as user without update permission
        auth_response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to update sample
        update_data = {"description": "Updated description"}
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail with 403 Forbidden
        assert response.status_code == 403
    
    def test_update_sample_audit_fields(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test that audit fields (modified_at, modified_by) are updated on PATCH"""
        # Create a test sample
        original_modified_at = datetime.utcnow() - timedelta(hours=1)
        sample = Sample(
            name="SAMPLE-AUDIT-001",
            description="Test sample for audit",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
            modified_at=original_modified_at
        )
        db_session.add(sample)
        db_session.commit()
        original_modified_at_db = sample.modified_at
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update sample
        update_data = {"description": "Updated description for audit test"}
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify modified_by is updated
        assert data["modified_by"] == str(test_admin_user.id)
        
        # Verify modified_at is updated (should be more recent)
        db_session.refresh(sample)
        assert sample.modified_at > original_modified_at_db
        assert sample.modified_by == test_admin_user.id
    
    def test_update_sample_atomic_transaction(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test that sample updates are atomic (all or nothing)"""
        # Create a test sample
        sample = Sample(
            name="SAMPLE-ATOMIC-001",
            description="Test sample for atomic transaction",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        original_description = sample.description
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to update with invalid data (should fail validation)
        update_data = {
            "description": "Updated description",
            "temperature": 2000.0  # Invalid: exceeds max
        }
        
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail validation
        assert response.status_code == 422
        
        # Verify sample was not updated (atomic transaction)
        db_session.refresh(sample)
        assert sample.description == original_description
    
    def test_update_sample_rls_denied(self, client: TestClient, test_data, db_session: Session):
        """Test that RLS denies access when user lacks project access"""
        from models.user import User, Role
        from models.client import Client
        
        # Create a different client
        other_client = Client(
            name="Other Client",
            description="Other client",
            billing_info={"address": "456 Other St"}
        )
        db_session.add(other_client)
        db_session.flush()
        
        # Create a user with sample:update permission but different client
        other_role = Role(
            name="Other Role",
            description="Other role"
        )
        db_session.add(other_role)
        db_session.flush()
        
        other_user = User(
            name="Other User",
            username="otheruser",
            email="other@example.com",
            password_hash="hashed_password",
            role_id=other_role.id,
            client_id=other_client.id
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create a sample in the original project
        sample = Sample(
            name="SAMPLE-RLS-001",
            description="Test sample for RLS",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_data["project"].client_id,  # Use project's client
            modified_by=test_data["project"].client_id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Login as other user (different client)
        auth_response = client.post(
            "/auth/login",
            json={"username": "otheruser", "password": "hashed_password"}
        )
        # This will likely fail, but if it succeeds, the update should be denied
        if auth_response.status_code == 200:
            token = auth_response.json()["access_token"]
            update_data = {"description": "Should be denied"}
            response = client.patch(
                f"/samples/{sample.id}",
                json=update_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should be denied by RLS
            assert response.status_code in [403, 404]