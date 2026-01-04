"""
Tests for tests endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.test import Test
from models.sample import Sample
from models.analysis import Analysis
from models.project import Project
from models.client import Client
from models.list import ListEntry
from app.core.security import create_access_token
from datetime import datetime, timedelta
from uuid import uuid4


class TestTestsCRUD:
    """Test tests CRUD operations"""
    
    @pytest.fixture
    def test_data(self, db_session: Session):
        """Create test data for tests"""
        # Create client and project
        client = Client(
            name="Test Client",
            description="Test client for tests",
            billing_info={"address": "123 Test St"}
        )
        db_session.add(client)
        db_session.flush()
        
        project = Project(
            name="Test Project",
            description="Test project for tests",
            start_date=datetime.utcnow(),
            client_id=client.id,
            status=uuid4()
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="SAMPLE-TEST-001",
            description="Test sample for tests",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=uuid4(),
            status=uuid4(),
            matrix=uuid4(),
            temperature=25.0,
            project_id=project.id,
            created_by=uuid4(),
            modified_by=uuid4()
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis",
            description="Test analysis for tests",
            method="Test Method",
            turnaround_time=24,
            cost=100.0,
            created_by=uuid4(),
            modified_by=uuid4()
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create test status
        test_status = ListEntry(
            list_id=uuid4(),
            name="In Process",
            description="Test in process status"
        )
        db_session.add(test_status)
        db_session.flush()
        
        return {
            "client": client,
            "project": project,
            "sample": sample,
            "analysis": analysis,
            "test_status": test_status
        }
    
    def test_create_test_success(self, client: TestClient, test_admin_user, test_data):
        """Test successful test creation"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        test_data_dict = {
            "name": "TEST-001",
            "description": "Test test",
            "sample_id": str(test_data["sample"].id),
            "analysis_id": str(test_data["analysis"].id),
            "status": str(test_data["test_status"].id),
            "technician_id": str(test_admin_user.id)
        }
        
        response = client.post(
            "/tests/",
            json=test_data_dict,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "TEST-001"
        assert data["description"] == "Test test"
        assert data["sample_id"] == str(test_data["sample"].id)
        assert data["analysis_id"] == str(test_data["analysis"].id)
    
    def test_get_tests_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful tests retrieval"""
        # Create a test
        test = Test(
            name="TEST-002",
            description="Test test for retrieval",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/tests/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tests" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["tests"]) >= 1
    
    def test_get_test_by_id_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful test retrieval by ID"""
        # Create a test
        test = Test(
            name="TEST-003",
            description="Test test for ID retrieval",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            f"/tests/{test.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test.id)
        assert data["name"] == "TEST-003"
    
    def test_update_test_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful test update"""
        # Create a test
        test = Test(
            name="TEST-004",
            description="Test test for update",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update test
        update_data = {
            "description": "Updated test description",
            "test_date": datetime.utcnow().isoformat()
        }
        
        response = client.patch(
            f"/tests/{test.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated test description"
    
    def test_delete_test_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful test deletion"""
        # Create a test
        test = Test(
            name="TEST-005",
            description="Test test for deletion",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Delete test
        response = client.delete(
            f"/tests/{test.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify test is soft deleted
        db_session.refresh(test)
        assert test.active == False


class TestTestAssignment:
    """Test test assignment workflow"""
    
    def test_assign_test_to_sample_success(self, client: TestClient, test_admin_user, test_data):
        """Test successful test assignment to sample"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        assignment_data = {
            "sample_id": str(test_data["sample"].id),
            "analysis_id": str(test_data["analysis"].id),
            "technician_id": str(test_admin_user.id),
            "test_date": datetime.utcnow().isoformat()
        }
        
        response = client.post(
            "/tests/assign",
            json=assignment_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["sample_id"] == str(test_data["sample"].id)
        assert data["analysis_id"] == str(test_data["analysis"].id)
        assert data["technician_id"] == str(test_admin_user.id)
    
    def test_assign_test_invalid_sample(self, client: TestClient, test_admin_user, test_data):
        """Test test assignment with invalid sample ID"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        assignment_data = {
            "sample_id": str(uuid4()),  # Non-existent sample
            "analysis_id": str(test_data["analysis"].id),
            "technician_id": str(test_admin_user.id)
        }
        
        response = client.post(
            "/tests/assign",
            json=assignment_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Sample not found" in response.json()["detail"]
    
    def test_assign_test_invalid_analysis(self, client: TestClient, test_admin_user, test_data):
        """Test test assignment with invalid analysis ID"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        assignment_data = {
            "sample_id": str(test_data["sample"].id),
            "analysis_id": str(uuid4()),  # Non-existent analysis
            "technician_id": str(test_admin_user.id)
        }
        
        response = client.post(
            "/tests/assign",
            json=assignment_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Invalid analysis ID" in response.json()["detail"]


class TestTestStatusManagement:
    """Test test status management"""
    
    def test_update_test_status_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful test status update"""
        # Create a test
        test = Test(
            name="TEST-006",
            description="Test test for status update",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        # Create new status
        new_status = ListEntry(
            list_id=uuid4(),
            name="In Analysis",
            description="Test in analysis status"
        )
        db_session.add(new_status)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update status
        status_data = {
            "status": str(new_status.id),
            "test_date": datetime.utcnow().isoformat()
        }
        
        response = client.patch(
            f"/tests/{test.id}/status",
            json=status_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == str(new_status.id)
    
    def test_update_test_status_invalid(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test test status update with invalid status ID"""
        # Create a test
        test = Test(
            name="TEST-007",
            description="Test test for invalid status update",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update with invalid status
        status_data = {
            "status": str(uuid4()),  # Non-existent status
            "test_date": datetime.utcnow().isoformat()
        }
        
        response = client.patch(
            f"/tests/{test.id}/status",
            json=status_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Invalid status ID" in response.json()["detail"]


class TestTestReview:
    """Test test review workflow"""
    
    def test_review_test_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful test review"""
        # Create a test
        test = Test(
            name="TEST-008",
            description="Test test for review",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Review test
        review_data = {
            "review_date": datetime.utcnow().isoformat(),
            "notes": "Test review completed successfully"
        }
        
        response = client.patch(
            f"/tests/{test.id}/review",
            json=review_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["review_date"] is not None
    
    def test_review_test_not_found(self, client: TestClient, test_admin_user):
        """Test test review with non-existent test ID"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        review_data = {
            "review_date": datetime.utcnow().isoformat(),
            "notes": "Test review"
        }
        
        response = client.patch(
            f"/tests/{uuid4()}/review",
            json=review_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Test not found" in response.json()["detail"]


class TestTestPermissions:
    """Test test permission requirements"""
    
    def test_create_test_requires_permission(self, client: TestClient, test_user):
        """Test that creating tests requires proper permission"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to create test (should fail due to missing data)
        test_data = {
            "name": "TEST-009",
            "description": "Test test",
            "sample_id": str(uuid4()),
            "analysis_id": str(uuid4()),
            "status": str(uuid4())
        }
        
        response = client.post(
            "/tests/",
            json=test_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail due to missing data or permissions
        assert response.status_code in [400, 403, 404]
    
    def test_get_tests_requires_permission(self, client: TestClient):
        """Test that getting tests requires authentication"""
        response = client.get("/tests/")
        assert response.status_code == 401  # Unauthorized
    
    def test_update_test_requires_permission(self, client: TestClient):
        """Test that updating tests requires authentication"""
        response = client.patch(
            f"/tests/{uuid4()}",
            json={"description": "Updated"}
        )
        assert response.status_code == 401  # Unauthorized
    
    def test_update_test_with_custom_attributes(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test updating test with custom attributes"""
        # Create a test
        test = Test(
            name="TEST-CUSTOM-001",
            description="Test test for custom attributes",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update test with custom attributes
        update_data = {
            "custom_attributes": {
                "instrument": "GC-MS-001",
                "run_number": "2025-001"
            }
        }
        
        response = client.patch(
            f"/tests/{test.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "custom_attributes" in data
        assert data["custom_attributes"]["instrument"] == "GC-MS-001"
        assert data["custom_attributes"]["run_number"] == "2025-001"
    
    def test_update_test_not_found(self, client: TestClient, test_admin_user):
        """Test updating non-existent test"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.patch(
            f"/tests/{uuid4()}",
            json={"description": "Updated"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Test not found" in response.json()["detail"]
    
    def test_update_test_status_example(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test updating test status (example from docstring)"""
        # Create complete status
        from models.list import List, ListEntry
        test_status_list = db_session.query(List).filter(List.name == "Test Status").first()
        if not test_status_list:
            test_status_list = List(
                name="Test Status",
                description="Test status values"
            )
            db_session.add(test_status_list)
            db_session.flush()
        
        complete_status = ListEntry(
            list_id=test_status_list.id,
            name="Complete",
            description="Test complete"
        )
        db_session.add(complete_status)
        db_session.flush()
        
        # Create a test
        test = Test(
            name="TEST-STATUS-001",
            description="Test test for status update",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update status
        update_data = {
            "status": str(complete_status.id)
        }
        
        response = client.patch(
            f"/tests/{test.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == str(complete_status.id)
    
    def test_update_test_technician_assignment(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test updating technician assignment (example from docstring)"""
        # Create a test
        test = Test(
            name="TEST-TECH-001",
            description="Test test for technician update",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update technician and test date
        update_data = {
            "technician_id": str(test_admin_user.id),
            "test_date": datetime.utcnow().isoformat()
        }
        
        response = client.patch(
            f"/tests/{test.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["technician_id"] == str(test_admin_user.id)
        assert data["test_date"] is not None


class TestTestEditRBAC:
    """Test RBAC for test editing operations"""
    
    def test_update_test_requires_update_permission(self, client: TestClient, test_user, test_data, db_session: Session):
        """Test that updating tests requires test:update permission"""
        # Create a test
        test = Test(
            name="TEST-RBAC-001",
            description="Test test for RBAC",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_user.id,
            created_by=test_user.id,
            modified_by=test_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        # Login as user without update permission
        auth_response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to update test
        update_data = {"description": "Updated description"}
        response = client.patch(
            f"/tests/{test.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail with 403 Forbidden
        assert response.status_code == 403
    
    def test_update_test_audit_fields(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test that audit fields (modified_at, modified_by) are updated on PATCH"""
        # Create a test
        original_modified_at = datetime.utcnow() - timedelta(hours=1)
        test = Test(
            name="TEST-AUDIT-001",
            description="Test test for audit",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id,
            modified_at=original_modified_at
        )
        db_session.add(test)
        db_session.commit()
        original_modified_at_db = test.modified_at
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update test
        update_data = {"description": "Updated description for audit test"}
        response = client.patch(
            f"/tests/{test.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify modified_by is updated
        assert data["modified_by"] == str(test_admin_user.id)
        
        # Verify modified_at is updated (should be more recent)
        db_session.refresh(test)
        assert test.modified_at > original_modified_at_db
        assert test.modified_by == test_admin_user.id
    
    def test_update_test_atomic_transaction(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test that test updates are atomic (all or nothing)"""
        # Create a test
        test = Test(
            name="TEST-ATOMIC-001",
            description="Test test for atomic transaction",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        original_description = test.description
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to update with invalid data (future date)
        future_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
        update_data = {
            "description": "Updated description",
            "test_date": future_date  # Invalid: future date
        }
        
        response = client.patch(
            f"/tests/{test.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail validation
        assert response.status_code == 422
        
        # Verify test was not updated (atomic transaction)
        db_session.refresh(test)
        assert test.description == original_description


class TestTestValidation:
    """Test test validation"""
    
    def test_create_test_validation_error(self, client: TestClient, test_admin_user):
        """Test test creation with validation errors"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Test with missing required fields
        test_data = {
            "name": "TEST-010",
            # Missing required fields
        }
        
        response = client.post(
            "/tests/",
            json=test_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_update_test_status_future_date(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test test status update with future date"""
        # Create a test
        test = Test(
            name="TEST-011",
            description="Test test for future date validation",
            sample_id=test_data["sample"].id,
            analysis_id=test_data["analysis"].id,
            status=test_data["test_status"].id,
            technician_id=test_admin_user.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test)
        db_session.commit()
        
        # Create new status
        new_status = ListEntry(
            list_id=uuid4(),
            name="Complete",
            description="Test complete status"
        )
        db_session.add(new_status)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update with future date
        status_data = {
            "status": str(new_status.id),
            "test_date": (datetime.utcnow() + timedelta(days=1)).isoformat()  # Future date
        }
        
        response = client.patch(
            f"/tests/{test.id}/status",
            json=status_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error
        assert "Date cannot be in the future" in response.json()["detail"]
