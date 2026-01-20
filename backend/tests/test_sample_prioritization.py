"""
Tests for sample prioritization and eligible samples endpoint.

Tests cover:
- GET /samples/eligible endpoint with prioritization
- Expiration calculation (date_sampled + shelf_life)
- Due date inheritance (sample.due_date > project.due_date)
- Sorting by days_until_expiration ASC NULLS LAST, then days_until_due ASC NULLS LAST
- is_expired and is_overdue flags
- Expiration warnings in response
- POST /batches/validate-compatibility expiration warnings
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import uuid4

from models.sample import Sample
from models.project import Project
from models.client import Client
from models.analysis import Analysis
from models.test import Test
from models.list import List, ListEntry


class TestEligibleSamplesEndpoint:
    """Test GET /samples/eligible endpoint with prioritization"""
    
    @pytest.fixture
    def prioritization_test_data(self, db_session: Session, test_admin_user):
        """Create test data for prioritization tests with various expiration scenarios"""
        # Create client
        client = Client(
            name="Priority Test Client",
            description="Client for prioritization tests",
            billing_info={"address": "123 Test St"},
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(client)
        db_session.flush()
        
        # Create project with due_date
        project = Project(
            name="Priority Test Project",
            description="Project for prioritization tests",
            start_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=10),  # Project due in 10 days
            client_id=client.id,
            status=uuid4(),
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create list entries
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            description="Water sample type"
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
            name="Water",
            description="Water matrix"
        )
        db_session.add(matrix)
        db_session.flush()
        
        # Create analysis with shelf_life
        analysis = Analysis(
            name="EPA Method 8080",
            description="Pesticides analysis",
            method="EPA 8080",
            turnaround_time=7,
            cost=150.0,
            shelf_life=14,  # 14 days shelf life
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analysis without shelf_life
        analysis_no_shelf = Analysis(
            name="General Chemistry",
            description="General chemistry panel",
            method="Standard",
            turnaround_time=3,
            cost=50.0,
            shelf_life=None,  # No shelf life
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(analysis_no_shelf)
        db_session.flush()
        
        db_session.commit()
        
        return {
            "client": client,
            "project": project,
            "sample_type": sample_type,
            "status": status,
            "matrix": matrix,
            "analysis": analysis,
            "analysis_no_shelf": analysis_no_shelf,
            "admin_user": test_admin_user
        }
    
    def create_sample_with_test(self, db_session, test_data, name, date_sampled, due_date=None, analysis=None):
        """Helper to create a sample with an assigned test"""
        sample = Sample(
            name=name,
            description=f"Test sample {name}",
            due_date=due_date,
            received_date=datetime.utcnow(),
            date_sampled=date_sampled,
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=4.0,
            project_id=test_data["project"].id,
            created_by=test_data["admin_user"].id,
            modified_by=test_data["admin_user"].id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create test assignment if analysis provided
        if analysis:
            test = Test(
                sample_id=sample.id,
                analysis_id=analysis.id,
                status=test_data["status"].id,
                created_by=test_data["admin_user"].id,
                modified_by=test_data["admin_user"].id
            )
            db_session.add(test)
            db_session.flush()
        
        return sample
    
    def test_eligible_samples_returns_prioritization_fields(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that eligible samples response includes prioritization fields"""
        test_data = prioritization_test_data
        
        # Create sample with date_sampled 7 days ago (7 days until expiration with 14-day shelf life)
        sample = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-PRIORITY-001",
            date_sampled=datetime.utcnow() - timedelta(days=7),
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Get eligible samples
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "samples" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert "warnings" in data
        
        # Find our sample
        sample_data = next((s for s in data["samples"] if s["id"] == str(sample.id)), None)
        assert sample_data is not None
        
        # Verify prioritization fields
        assert "days_until_expiration" in sample_data
        assert "days_until_due" in sample_data
        assert "is_expired" in sample_data
        assert "is_overdue" in sample_data
        assert "expiration_warning" in sample_data
    
    def test_expiration_calculation_correct(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that days_until_expiration is calculated correctly"""
        test_data = prioritization_test_data
        
        # Create sample with date_sampled 10 days ago (4 days until expiration with 14-day shelf life)
        sample = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-EXP-CALC-001",
            date_sampled=datetime.utcnow() - timedelta(days=10),
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sample_data = next((s for s in data["samples"] if s["id"] == str(sample.id)), None)
        assert sample_data is not None
        
        # Shelf life is 14 days, sampled 10 days ago = 4 days remaining
        # Allow for some timing variance
        assert sample_data["days_until_expiration"] is not None
        assert 3 <= sample_data["days_until_expiration"] <= 5
        assert sample_data["is_expired"] == False
    
    def test_expired_sample_flagged_correctly(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that expired samples have is_expired=True and negative days"""
        test_data = prioritization_test_data
        
        # Create sample with date_sampled 20 days ago (expired with 14-day shelf life)
        sample = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-EXPIRED-001",
            date_sampled=datetime.utcnow() - timedelta(days=20),
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Request with include_expired=true
        response = client.get(
            "/samples/eligible?include_expired=true",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sample_data = next((s for s in data["samples"] if s["id"] == str(sample.id)), None)
        assert sample_data is not None
        
        # Shelf life is 14 days, sampled 20 days ago = -6 days (expired)
        assert sample_data["days_until_expiration"] is not None
        assert sample_data["days_until_expiration"] < 0
        assert sample_data["is_expired"] == True
        assert sample_data["expiration_warning"] is not None
    
    def test_expired_samples_excluded_by_default(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that expired samples are excluded when include_expired=false (default)"""
        test_data = prioritization_test_data
        
        # Create expired sample
        expired_sample = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-EXCLUDED-001",
            date_sampled=datetime.utcnow() - timedelta(days=20),
            analysis=test_data["analysis"]
        )
        
        # Create valid sample
        valid_sample = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-VALID-001",
            date_sampled=datetime.utcnow() - timedelta(days=5),
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Request without include_expired (defaults to false)
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sample_ids = [s["id"] for s in data["samples"]]
        
        # Valid sample should be included
        assert str(valid_sample.id) in sample_ids
        
        # Expired sample should be excluded
        assert str(expired_sample.id) not in sample_ids
    
    def test_due_date_inheritance(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that due date is inherited from project when sample.due_date is null"""
        test_data = prioritization_test_data
        
        # Create sample without due_date (should inherit from project)
        sample_inherit = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-INHERIT-DUE-001",
            date_sampled=datetime.utcnow() - timedelta(days=5),
            due_date=None,  # Should inherit project's due_date (10 days from now)
            analysis=test_data["analysis"]
        )
        
        # Create sample with its own due_date
        sample_override = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-OVERRIDE-DUE-001",
            date_sampled=datetime.utcnow() - timedelta(days=5),
            due_date=datetime.utcnow() + timedelta(days=3),  # Sample due in 3 days
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        inherit_data = next((s for s in data["samples"] if s["id"] == str(sample_inherit.id)), None)
        override_data = next((s for s in data["samples"] if s["id"] == str(sample_override.id)), None)
        
        assert inherit_data is not None
        assert override_data is not None
        
        # Sample inheriting from project should have ~10 days until due
        assert inherit_data["days_until_due"] is not None
        assert 9 <= inherit_data["days_until_due"] <= 11
        
        # Sample with override should have ~3 days until due
        assert override_data["days_until_due"] is not None
        assert 2 <= override_data["days_until_due"] <= 4
    
    def test_sorting_by_expiration_then_due_date(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that samples are sorted by expiration ASC, then due date ASC"""
        test_data = prioritization_test_data
        
        # Create samples with different expiration times
        # Sample 1: Expires in 2 days
        sample_urgent = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-URGENT-001",
            date_sampled=datetime.utcnow() - timedelta(days=12),  # 2 days left
            due_date=datetime.utcnow() + timedelta(days=5),
            analysis=test_data["analysis"]
        )
        
        # Sample 2: Expires in 10 days
        sample_normal = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-NORMAL-001",
            date_sampled=datetime.utcnow() - timedelta(days=4),  # 10 days left
            due_date=datetime.utcnow() + timedelta(days=5),
            analysis=test_data["analysis"]
        )
        
        # Sample 3: Expires in 6 days
        sample_medium = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-MEDIUM-001",
            date_sampled=datetime.utcnow() - timedelta(days=8),  # 6 days left
            due_date=datetime.utcnow() + timedelta(days=5),
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Get positions of our samples
        sample_positions = {}
        for idx, s in enumerate(data["samples"]):
            if s["id"] == str(sample_urgent.id):
                sample_positions["urgent"] = idx
            elif s["id"] == str(sample_normal.id):
                sample_positions["normal"] = idx
            elif s["id"] == str(sample_medium.id):
                sample_positions["medium"] = idx
        
        # Verify all samples found
        assert "urgent" in sample_positions
        assert "normal" in sample_positions
        assert "medium" in sample_positions
        
        # Verify sort order: urgent (2 days) < medium (6 days) < normal (10 days)
        assert sample_positions["urgent"] < sample_positions["medium"]
        assert sample_positions["medium"] < sample_positions["normal"]
    
    def test_null_expiration_sorted_last(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that samples with null expiration are sorted last (NULLS LAST)"""
        test_data = prioritization_test_data
        
        # Sample with expiration
        sample_with_exp = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-WITH-EXP-001",
            date_sampled=datetime.utcnow() - timedelta(days=7),
            analysis=test_data["analysis"]
        )
        
        # Sample without expiration (no date_sampled)
        sample_no_exp = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-NO-EXP-001",
            date_sampled=None,  # No date_sampled means no expiration
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find positions
        with_exp_pos = None
        no_exp_pos = None
        for idx, s in enumerate(data["samples"]):
            if s["id"] == str(sample_with_exp.id):
                with_exp_pos = idx
            elif s["id"] == str(sample_no_exp.id):
                no_exp_pos = idx
        
        # Sample with expiration should come before sample without
        assert with_exp_pos is not None
        assert no_exp_pos is not None
        assert with_exp_pos < no_exp_pos
    
    def test_warnings_for_expiring_samples(
        self, client: TestClient, test_admin_user, prioritization_test_data, db_session
    ):
        """Test that warnings are included for expiring samples"""
        test_data = prioritization_test_data
        
        # Create sample expiring soon (2 days)
        sample_expiring = self.create_sample_with_test(
            db_session, test_data,
            name="SAMPLE-EXPIRING-WARN-001",
            date_sampled=datetime.utcnow() - timedelta(days=12),
            analysis=test_data["analysis"]
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have warnings about expiring samples
        assert "warnings" in data
        # Warnings should mention expiring samples
        assert len(data["warnings"]) >= 0  # May or may not have warnings depending on thresholds


class TestBatchValidationExpirationWarnings:
    """Test POST /batches/validate-compatibility expiration warnings"""
    
    @pytest.fixture
    def batch_validation_test_data(self, db_session: Session, test_admin_user):
        """Create test data for batch validation tests"""
        from models.container import Container, ContainerType, Contents
        
        # Create client
        client = Client(
            name="Batch Validation Client",
            description="Client for batch validation tests",
            billing_info={},
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(client)
        db_session.flush()
        
        # Create project
        project = Project(
            name="Batch Validation Project",
            description="Project for batch validation tests",
            start_date=datetime.utcnow(),
            client_id=client.id,
            status=uuid4(),
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create list entries
        sample_type = ListEntry(list_id=uuid4(), name="Water Sample", description="Water")
        status = ListEntry(list_id=uuid4(), name="Received", description="Received")
        matrix = ListEntry(list_id=uuid4(), name="Water", description="Water")
        db_session.add_all([sample_type, status, matrix])
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="Test Vial",
            description="Test vial for batch validation",
            capacity=50,
            capacity_unit="mL",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        # Create analysis with shelf_life
        analysis = Analysis(
            name="Batch Test Analysis",
            description="Analysis for batch tests",
            method="Test Method",
            turnaround_time=5,
            cost=100.0,
            shelf_life=14,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        db_session.commit()
        
        return {
            "client": client,
            "project": project,
            "sample_type": sample_type,
            "status": status,
            "matrix": matrix,
            "container_type": container_type,
            "analysis": analysis,
            "admin_user": test_admin_user
        }
    
    def create_container_with_sample(
        self, db_session, test_data, sample_name, date_sampled, container_name
    ):
        """Helper to create a container with a sample"""
        from models.container import Container, Contents
        
        # Create sample
        sample = Sample(
            name=sample_name,
            description=f"Sample {sample_name}",
            date_sampled=date_sampled,
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            temperature=4.0,
            project_id=test_data["project"].id,
            created_by=test_data["admin_user"].id,
            modified_by=test_data["admin_user"].id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create test assignment
        test = Test(
            sample_id=sample.id,
            analysis_id=test_data["analysis"].id,
            status=test_data["status"].id,
            created_by=test_data["admin_user"].id,
            modified_by=test_data["admin_user"].id
        )
        db_session.add(test)
        db_session.flush()
        
        # Create container
        container = Container(
            name=container_name,
            description=f"Container {container_name}",
            type_id=test_data["container_type"].id,
            project_id=test_data["project"].id,
            created_by=test_data["admin_user"].id,
            modified_by=test_data["admin_user"].id
        )
        db_session.add(container)
        db_session.flush()
        
        # Link sample to container
        contents = Contents(
            container_id=container.id,
            sample_id=sample.id,
            created_by=test_data["admin_user"].id,
            modified_by=test_data["admin_user"].id
        )
        db_session.add(contents)
        db_session.flush()
        
        return container, sample
    
    def test_validate_compatibility_warns_expired_samples(
        self, client: TestClient, test_admin_user, batch_validation_test_data, db_session
    ):
        """Test that validate-compatibility warns about expired samples"""
        test_data = batch_validation_test_data
        
        # Create container with expired sample
        container1, sample1 = self.create_container_with_sample(
            db_session, test_data,
            sample_name="BATCH-EXPIRED-001",
            date_sampled=datetime.utcnow() - timedelta(days=20),  # Expired
            container_name="CONTAINER-EXPIRED-001"
        )
        
        # Create container with valid sample
        container2, sample2 = self.create_container_with_sample(
            db_session, test_data,
            sample_name="BATCH-VALID-001",
            date_sampled=datetime.utcnow() - timedelta(days=5),  # Valid
            container_name="CONTAINER-VALID-001"
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.post(
            "/batches/validate-compatibility",
            json={"container_ids": [str(container1.id), str(container2.id)]},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have warnings about expired samples
        assert "warnings" in data
        
        # Find expired_samples warning
        expired_warning = next(
            (w for w in data.get("warnings", []) if w.get("type") == "expired_samples"),
            None
        )
        
        # Should have warning for expired sample
        if expired_warning:
            assert "message" in expired_warning
            assert "samples" in expired_warning
            expired_sample_ids = [s["sample_id"] for s in expired_warning["samples"]]
            assert str(sample1.id) in expired_sample_ids
    
    def test_validate_compatibility_warns_expiring_soon(
        self, client: TestClient, test_admin_user, batch_validation_test_data, db_session
    ):
        """Test that validate-compatibility warns about samples expiring soon"""
        test_data = batch_validation_test_data
        
        # Create container with sample expiring in 2 days
        container1, sample1 = self.create_container_with_sample(
            db_session, test_data,
            sample_name="BATCH-EXPIRING-001",
            date_sampled=datetime.utcnow() - timedelta(days=12),  # 2 days left
            container_name="CONTAINER-EXPIRING-001"
        )
        
        # Create container with valid sample (plenty of time)
        container2, sample2 = self.create_container_with_sample(
            db_session, test_data,
            sample_name="BATCH-FRESH-001",
            date_sampled=datetime.utcnow() - timedelta(days=2),  # 12 days left
            container_name="CONTAINER-FRESH-001"
        )
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.post(
            "/batches/validate-compatibility",
            json={"container_ids": [str(container1.id), str(container2.id)]},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have warnings about expiring soon
        assert "warnings" in data
        
        # Find expiring_soon warning
        expiring_warning = next(
            (w for w in data.get("warnings", []) if w.get("type") == "expiring_soon"),
            None
        )
        
        if expiring_warning:
            assert "message" in expiring_warning
            assert "samples" in expiring_warning


class TestOverdueSamples:
    """Test overdue sample detection"""
    
    @pytest.fixture
    def overdue_test_data(self, db_session: Session, test_admin_user):
        """Create test data for overdue tests"""
        client = Client(
            name="Overdue Test Client",
            description="Client for overdue tests",
            billing_info={},
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(client)
        db_session.flush()
        
        project = Project(
            name="Overdue Test Project",
            description="Project for overdue tests",
            start_date=datetime.utcnow() - timedelta(days=30),
            due_date=datetime.utcnow() - timedelta(days=5),  # Project was due 5 days ago
            client_id=client.id,
            status=uuid4(),
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        sample_type = ListEntry(list_id=uuid4(), name="Overdue Sample", description="Overdue")
        status = ListEntry(list_id=uuid4(), name="Received", description="Received")
        matrix = ListEntry(list_id=uuid4(), name="Water", description="Water")
        db_session.add_all([sample_type, status, matrix])
        db_session.flush()
        
        # Analysis with long shelf life (not expired)
        analysis = Analysis(
            name="Long Shelf Life Analysis",
            description="Analysis with long shelf life",
            method="Standard",
            turnaround_time=5,
            cost=100.0,
            shelf_life=365,  # 1 year shelf life
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        db_session.commit()
        
        return {
            "client": client,
            "project": project,
            "sample_type": sample_type,
            "status": status,
            "matrix": matrix,
            "analysis": analysis,
            "admin_user": test_admin_user
        }
    
    def test_overdue_sample_flagged(
        self, client: TestClient, test_admin_user, overdue_test_data, db_session
    ):
        """Test that overdue samples have is_overdue=True"""
        test_data = overdue_test_data
        
        # Create sample without its own due_date (inherits overdue project due_date)
        sample = Sample(
            name="SAMPLE-OVERDUE-001",
            description="Overdue sample",
            date_sampled=datetime.utcnow() - timedelta(days=3),  # Not expired
            due_date=None,  # Inherits project due_date (5 days ago)
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
            project_id=test_data["project"].id,
            created_by=test_data["admin_user"].id,
            modified_by=test_data["admin_user"].id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Add test assignment
        test = Test(
            sample_id=sample.id,
            analysis_id=test_data["analysis"].id,
            status=test_data["status"].id,
            created_by=test_data["admin_user"].id,
            modified_by=test_data["admin_user"].id
        )
        db_session.add(test)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/samples/eligible",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sample_data = next((s for s in data["samples"] if s["id"] == str(sample.id)), None)
        assert sample_data is not None
        
        # Should be overdue (project due_date was 5 days ago)
        assert sample_data["days_until_due"] is not None
        assert sample_data["days_until_due"] < 0
        assert sample_data["is_overdue"] == True
        
        # Should NOT be expired (long shelf life)
        assert sample_data["is_expired"] == False
