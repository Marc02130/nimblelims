"""
Tests for bulk sample accessioning endpoint (US-24)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.sample import Sample
from models.project import Project
from models.client import Client
from models.list import List, ListEntry
from models.container import ContainerType, Container, Contents
from models.test import Test
from models.analysis import Analysis
from app.core.security import create_access_token
from datetime import datetime, timedelta
from uuid import uuid4, UUID


class TestBulkAccessioning:
    """Test bulk sample accessioning (US-24)"""
    
    @pytest.fixture
    def test_data(self, db_session: Session, test_admin_user):
        """Create test data for bulk accessioning tests"""
        # Create client
        client = Client(
            name="Test Client",
            description="Test client for bulk accessioning",
            billing_info={"address": "123 Test St"}
        )
        db_session.add(client)
        db_session.flush()
        
        # Create project
        project = Project(
            name="Test Project",
            description="Test project for bulk accessioning",
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
            description="Blood sample type",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Blood",
            description="Blood matrix",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(matrix)
        db_session.flush()
        
        # Create sample status list and entry
        sample_status_list = List(
            name="sample_status",
            description="Sample status list",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample_status_list)
        db_session.flush()
        
        received_status = ListEntry(
            list_id=sample_status_list.id,
            name="Received",
            description="Sample received",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(received_status)
        db_session.flush()
        
        # Create test status list and entry
        test_status_list = List(
            name="test_status",
            description="Test status list",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(test_status_list)
        db_session.flush()
        
        in_process_status = ListEntry(
            list_id=test_status_list.id,
            name="In Process",
            description="Test in process",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(in_process_status)
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="15mL Tube",
            description="15mL test tube",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.commit()
        
        return {
            "client": client,
            "project": project,
            "sample_type": sample_type,
            "matrix": matrix,
            "received_status": received_status,
            "in_process_status": in_process_status,
            "container_type": container_type
        }
    
    def test_bulk_accession_success(self, client: TestClient, test_admin_user, test_data):
        """Test successful bulk accessioning"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        bulk_data = {
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "container_type_id": str(test_data["container_type"].id),
            "uniques": [
                {
                    "name": "BULK-001",
                    "container_name": "CONTAINER-001",
                    "client_sample_id": "CLIENT-001"
                },
                {
                    "name": "BULK-002",
                    "container_name": "CONTAINER-002",
                    "client_sample_id": "CLIENT-002"
                }
            ]
        }
        
        response = client.post(
            "/samples/bulk-accession",
            json=bulk_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "BULK-001"
        assert data[1]["name"] == "BULK-002"
    
    def test_bulk_accession_with_auto_naming(self, client: TestClient, test_admin_user, test_data):
        """Test bulk accessioning with auto-generated names"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        bulk_data = {
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "container_type_id": str(test_data["container_type"].id),
            "auto_name_prefix": "AUTO-",
            "auto_name_start": 100,
            "uniques": [
                {
                    "container_name": "CONTAINER-AUTO-001"
                },
                {
                    "container_name": "CONTAINER-AUTO-002"
                }
            ]
        }
        
        response = client.post(
            "/samples/bulk-accession",
            json=bulk_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "AUTO-100"
        assert data[1]["name"] == "AUTO-101"
    
    def test_bulk_accession_duplicate_names(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test bulk accessioning fails with duplicate sample names"""
        # Create existing sample with duplicate name
        existing_sample = Sample(
            name="DUPLICATE-001",
            description="Existing sample",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["received_status"].id,
            matrix=test_data["matrix"].id,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(existing_sample)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        bulk_data = {
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "container_type_id": str(test_data["container_type"].id),
            "uniques": [
                {
                    "name": "DUPLICATE-001",  # Duplicate name
                    "container_name": "CONTAINER-001"
                }
            ]
        }
        
        response = client.post(
            "/samples/bulk-accession",
            json=bulk_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Duplicate sample names" in response.json()["detail"]
    
    def test_bulk_accession_duplicate_containers(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test bulk accessioning fails with duplicate container names"""
        # Create existing container with duplicate name
        existing_container = Container(
            name="DUPLICATE-CONTAINER",
            type_id=test_data["container_type"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(existing_container)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        bulk_data = {
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "container_type_id": str(test_data["container_type"].id),
            "uniques": [
                {
                    "name": "NEW-SAMPLE-001",
                    "container_name": "DUPLICATE-CONTAINER"  # Duplicate container name
                }
            ]
        }
        
        response = client.post(
            "/samples/bulk-accession",
            json=bulk_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Duplicate container names" in response.json()["detail"]
    
    def test_bulk_accession_with_tests(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test bulk accessioning with test assignments"""
        # Create analysis
        analysis = Analysis(
            name="Test Analysis",
            method="Test Method",
            turnaround_time=7,
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
        
        bulk_data = {
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "container_type_id": str(test_data["container_type"].id),
            "assigned_tests": [str(analysis.id)],
            "uniques": [
                {
                    "name": "TEST-BULK-001",
                    "container_name": "CONTAINER-TEST-001"
                }
            ]
        }
        
        response = client.post(
            "/samples/bulk-accession",
            json=bulk_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "TEST-BULK-001"
        
        # Verify test was created
        tests = db_session.query(Test).filter(
            Test.sample_id == UUID(data[0]["id"]),
            Test.active == True
        ).all()
        assert len(tests) == 1
        assert tests[0].analysis_id == analysis.id
    
    def test_bulk_accession_creates_containers_and_contents(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test that bulk accessioning creates containers and contents"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        bulk_data = {
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "container_type_id": str(test_data["container_type"].id),
            "uniques": [
                {
                    "name": "CONTENT-TEST-001",
                    "container_name": "CONTAINER-CONTENT-001"
                }
            ]
        }
        
        response = client.post(
            "/samples/bulk-accession",
            json=bulk_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        sample_id = UUID(data[0]["id"])
        
        # Verify container was created
        containers = db_session.query(Container).filter(
            Container.name == "CONTAINER-CONTENT-001",
            Container.active == True
        ).all()
        assert len(containers) == 1
        
        # Verify contents link was created
        contents = db_session.query(Contents).filter(
            Contents.sample_id == sample_id
        ).all()
        assert len(contents) == 1
        assert contents[0].container_id == containers[0].id

