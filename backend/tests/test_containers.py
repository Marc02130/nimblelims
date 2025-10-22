"""
Tests for containers endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.container import Container, ContainerType, Contents
from models.sample import Sample
from models.project import Project
from models.client import Client
from models.list import ListEntry
from models.unit import Unit
from app.core.security import create_access_token
from datetime import datetime, timedelta
from uuid import uuid4


class TestContainerTypesCRUD:
    """Test container types CRUD operations"""
    
    @pytest.fixture
    def test_data(self, db_session: Session):
        """Create test data for container tests"""
        # Create client and project
        client = Client(
            name="Test Client",
            description="Test client for containers",
            billing_info={"address": "123 Test St"}
        )
        db_session.add(client)
        db_session.flush()
        
        project = Project(
            name="Test Project",
            description="Test project for containers",
            start_date=datetime.utcnow(),
            client_id=client.id,
            status=uuid4()
        )
        db_session.add(project)
        db_session.flush()
        
        # Create units
        unit_type = ListEntry(
            list_id=uuid4(),
            name="volume",
            description="Volume unit type"
        )
        db_session.add(unit_type)
        db_session.flush()
        
        unit = Unit(
            name="mL",
            description="Milliliter",
            multiplier=0.001,  # 1 mL = 0.001 L
            type=unit_type.id,
            created_by=uuid4(),
            modified_by=uuid4()
        )
        db_session.add(unit)
        db_session.flush()
        
        return {
            "client": client,
            "project": project,
            "unit": unit
        }
    
    def test_create_container_type_success(self, client: TestClient, test_admin_user, test_data):
        """Test successful container type creation"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        container_type_data = {
            "name": "Test Tube",
            "description": "Standard test tube",
            "capacity": 5.0,
            "material": "Glass",
            "dimensions": "12x75",
            "preservative": "None"
        }
        
        response = client.post(
            "/containers/types",
            json=container_type_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Tube"
        assert data["capacity"] == 5.0
        assert data["material"] == "Glass"
    
    def test_get_container_types_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful container types retrieval"""
        # Create a test container type
        container_type = ContainerType(
            name="Test Plate",
            description="Test plate container",
            capacity=96.0,
            material="Plastic",
            dimensions="8x12",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/containers/types",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(ct["name"] == "Test Plate" for ct in data)
    
    def test_update_container_type_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful container type update"""
        # Create a test container type
        container_type = ContainerType(
            name="Test Container",
            description="Test container for update",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update container type
        update_data = {
            "description": "Updated test container",
            "capacity": 15.0
        }
        
        response = client.patch(
            f"/containers/types/{container_type.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated test container"
        assert data["capacity"] == 15.0


class TestContainersCRUD:
    """Test containers CRUD operations"""
    
    def test_create_container_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful container creation"""
        # Create container type
        container_type = ContainerType(
            name="Test Tube Type",
            description="Test tube container type",
            capacity=5.0,
            material="Glass",
            dimensions="12x75",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        container_data = {
            "name": "TUBE-001",
            "description": "Test tube container",
            "row": 1,
            "column": 1,
            "concentration": 10.0,
            "concentration_units": str(test_data["unit"].id),
            "amount": 5.0,
            "amount_units": str(test_data["unit"].id),
            "type_id": str(container_type.id)
        }
        
        response = client.post(
            "/containers/",
            json=container_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "TUBE-001"
        assert data["concentration"] == 10.0
        assert data["amount"] == 5.0
    
    def test_get_containers_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful containers retrieval"""
        # Create container type and container
        container_type = ContainerType(
            name="Test Plate Type",
            description="Test plate container type",
            capacity=96.0,
            material="Plastic",
            dimensions="8x12",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="PLATE-001",
            description="Test plate container",
            row=1,
            column=1,
            concentration=1.0,
            concentration_units=test_data["unit"].id,
            amount=100.0,
            amount_units=test_data["unit"].id,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            "/containers/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(c["name"] == "PLATE-001" for c in data)
    
    def test_get_container_by_id_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful container retrieval by ID"""
        # Create container type and container
        container_type = ContainerType(
            name="Test Container Type",
            description="Test container type",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="CONTAINER-001",
            description="Test container for ID retrieval",
            row=1,
            column=1,
            concentration=5.0,
            concentration_units=test_data["unit"].id,
            amount=10.0,
            amount_units=test_data["unit"].id,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            f"/containers/{container.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(container.id)
        assert data["name"] == "CONTAINER-001"
        assert "contents" in data
    
    def test_update_container_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful container update"""
        # Create container type and container
        container_type = ContainerType(
            name="Test Container Type",
            description="Test container type",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="CONTAINER-002",
            description="Test container for update",
            row=1,
            column=1,
            concentration=5.0,
            concentration_units=test_data["unit"].id,
            amount=10.0,
            amount_units=test_data["unit"].id,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update container
        update_data = {
            "description": "Updated container",
            "concentration": 7.5
        }
        
        response = client.patch(
            f"/containers/{container.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated container"
        assert data["concentration"] == 7.5


class TestContentsManagement:
    """Test container contents management"""
    
    def test_add_sample_to_container_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful sample addition to container"""
        # Create container type and container
        container_type = ContainerType(
            name="Test Container Type",
            description="Test container type",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="CONTAINER-003",
            description="Test container for contents",
            row=1,
            column=1,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="SAMPLE-001",
            description="Test sample for contents",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=uuid4(),
            status=uuid4(),
            matrix=uuid4(),
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
        
        # Add sample to container
        contents_data = {
            "container_id": str(container.id),
            "sample_id": str(sample.id),
            "concentration": 2.5,
            "concentration_units": str(test_data["unit"].id),
            "amount": 5.0,
            "amount_units": str(test_data["unit"].id)
        }
        
        response = client.post(
            f"/containers/{container.id}/contents",
            json=contents_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["container_id"] == str(container.id)
        assert data["sample_id"] == str(sample.id)
        assert data["concentration"] == 2.5
        assert data["amount"] == 5.0
    
    def test_get_container_contents_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful container contents retrieval"""
        # Create container type, container, and sample
        container_type = ContainerType(
            name="Test Container Type",
            description="Test container type",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="CONTAINER-004",
            description="Test container for contents retrieval",
            row=1,
            column=1,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        sample = Sample(
            name="SAMPLE-002",
            description="Test sample for contents retrieval",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=uuid4(),
            status=uuid4(),
            matrix=uuid4(),
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create contents
        contents = Contents(
            container_id=container.id,
            sample_id=sample.id,
            concentration=3.0,
            concentration_units=test_data["unit"].id,
            amount=6.0,
            amount_units=test_data["unit"].id
        )
        db_session.add(contents)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.get(
            f"/containers/{container.id}/contents",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "contents" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["contents"]) >= 1
    
    def test_update_container_contents_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful container contents update"""
        # Create container type, container, and sample
        container_type = ContainerType(
            name="Test Container Type",
            description="Test container type",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="CONTAINER-005",
            description="Test container for contents update",
            row=1,
            column=1,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        sample = Sample(
            name="SAMPLE-003",
            description="Test sample for contents update",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=uuid4(),
            status=uuid4(),
            matrix=uuid4(),
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create contents
        contents = Contents(
            container_id=container.id,
            sample_id=sample.id,
            concentration=1.0,
            concentration_units=test_data["unit"].id,
            amount=2.0,
            amount_units=test_data["unit"].id
        )
        db_session.add(contents)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update contents
        update_data = {
            "concentration": 4.0,
            "amount": 8.0
        }
        
        response = client.patch(
            f"/containers/{container.id}/contents/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["concentration"] == 4.0
        assert data["amount"] == 8.0
    
    def test_remove_sample_from_container_success(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test successful sample removal from container"""
        # Create container type, container, and sample
        container_type = ContainerType(
            name="Test Container Type",
            description="Test container type",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="CONTAINER-006",
            description="Test container for sample removal",
            row=1,
            column=1,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        sample = Sample(
            name="SAMPLE-004",
            description="Test sample for removal",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=uuid4(),
            status=uuid4(),
            matrix=uuid4(),
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create contents
        contents = Contents(
            container_id=container.id,
            sample_id=sample.id,
            concentration=2.0,
            concentration_units=test_data["unit"].id,
            amount=4.0,
            amount_units=test_data["unit"].id
        )
        db_session.add(contents)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Remove sample from container
        response = client.delete(
            f"/containers/{container.id}/contents/{sample.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "removed successfully" in response.json()["message"]


class TestContainerValidation:
    """Test container validation"""
    
    def test_create_container_invalid_type(self, client: TestClient, test_admin_user):
        """Test container creation with invalid type ID"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        container_data = {
            "name": "INVALID-CONTAINER",
            "description": "Container with invalid type",
            "type_id": str(uuid4())  # Non-existent type ID
        }
        
        response = client.post(
            "/containers/",
            json=container_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Invalid container type ID" in response.json()["detail"]
    
    def test_add_sample_to_container_duplicate(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test adding duplicate sample to container"""
        # Create container type and container
        container_type = ContainerType(
            name="Test Container Type",
            description="Test container type",
            capacity=10.0,
            material="Glass",
            dimensions="15x100",
            preservative="None",
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(
            name="CONTAINER-007",
            description="Test container for duplicate test",
            row=1,
            column=1,
            type_id=container_type.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="SAMPLE-005",
            description="Test sample for duplicate test",
            due_date=datetime.utcnow() + timedelta(days=7),
            received_date=datetime.utcnow(),
            sample_type=uuid4(),
            status=uuid4(),
            matrix=uuid4(),
            temperature=25.0,
            project_id=test_data["project"].id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create existing contents
        contents = Contents(
            container_id=container.id,
            sample_id=sample.id,
            concentration=1.0,
            concentration_units=test_data["unit"].id,
            amount=2.0,
            amount_units=test_data["unit"].id
        )
        db_session.add(contents)
        db_session.commit()
        
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Try to add same sample again
        contents_data = {
            "container_id": str(container.id),
            "sample_id": str(sample.id),
            "concentration": 3.0,
            "concentration_units": str(test_data["unit"].id),
            "amount": 6.0,
            "amount_units": str(test_data["unit"].id)
        }
        
        response = client.post(
            f"/containers/{container.id}/contents",
            json=contents_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Sample already exists in this container" in response.json()["detail"]
