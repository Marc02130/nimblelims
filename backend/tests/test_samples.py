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
