"""
Tests for custom attributes endpoints and validation
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.custom_attributes_config import CustomAttributeConfig
from models.sample import Sample
from models.test import Test
from models.project import Project
from models.client import Client
from models.list import List, ListEntry
from app.core.security import create_access_token
from datetime import datetime
from uuid import uuid4


class TestCustomAttributesConfig:
    """Test custom attributes configuration CRUD operations"""
    
    def test_create_custom_attribute_config_success(self, client: TestClient, test_admin_user, db_session: Session):
        """Test successful custom attribute configuration creation"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create config
        config_data = {
            "entity_type": "samples",
            "attr_name": "ph_level",
            "data_type": "number",
            "validation_rules": {"min": 0, "max": 14},
            "description": "pH level of the sample",
            "active": True
        }
        
        response = client.post(
            "/admin/custom-attributes",
            json=config_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["entity_type"] == "samples"
        assert data["attr_name"] == "ph_level"
        assert data["data_type"] == "number"
        assert data["active"] is True
    
    def test_create_custom_attribute_config_duplicate(self, client: TestClient, test_admin_user, db_session: Session):
        """Test that duplicate configs are rejected"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create first config
        config_data = {
            "entity_type": "samples",
            "attr_name": "ph_level",
            "data_type": "number",
            "validation_rules": {"min": 0, "max": 14},
            "active": True
        }
        
        response = client.post(
            "/admin/custom-attributes",
            json=config_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        
        # Try to create duplicate
        response = client.post(
            "/admin/custom-attributes",
            json=config_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_get_custom_attribute_configs(self, client: TestClient, test_admin_user, db_session: Session):
        """Test listing custom attribute configurations"""
        # Create test configs
        config1 = CustomAttributeConfig(
            id=uuid4(),
            name="ph_level_config",
            entity_type="samples",
            attr_name="ph_level",
            data_type="number",
            validation_rules={"min": 0, "max": 14},
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        config2 = CustomAttributeConfig(
            id=uuid4(),
            name="temperature_config",
            entity_type="samples",
            attr_name="storage_temp",
            data_type="number",
            validation_rules={"min": -20, "max": 40},
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add_all([config1, config2])
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # List configs
        response = client.get(
            "/admin/custom-attributes",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["configs"]) >= 2
    
    def test_update_custom_attribute_config(self, client: TestClient, test_admin_user, db_session: Session):
        """Test updating custom attribute configuration"""
        # Create config
        config = CustomAttributeConfig(
            id=uuid4(),
            name="ph_level_config",
            entity_type="samples",
            attr_name="ph_level",
            data_type="number",
            validation_rules={"min": 0, "max": 14},
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(config)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update config
        update_data = {
            "validation_rules": {"min": 1, "max": 13},
            "description": "Updated pH level"
        }
        
        response = client.patch(
            f"/admin/custom-attributes/{config.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation_rules"]["min"] == 1
        assert data["description"] == "Updated pH level"
    
    def test_delete_custom_attribute_config(self, client: TestClient, test_admin_user, db_session: Session):
        """Test soft-deleting custom attribute configuration"""
        # Create config
        config = CustomAttributeConfig(
            id=uuid4(),
            name="ph_level_config",
            entity_type="samples",
            attr_name="ph_level",
            data_type="number",
            validation_rules={"min": 0, "max": 14},
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(config)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Delete config (soft delete)
        response = client.delete(
            f"/admin/custom-attributes/{config.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 204
        
        # Verify it's inactive
        db_session.refresh(config)
        assert config.active is False


class TestCustomAttributesValidation:
    """Test custom attributes validation in samples and tests"""
    
    @pytest.fixture
    def test_data(self, db_session: Session, test_admin_user):
        """Create test data for validation tests"""
        # Create client and project
        client = Client(
            name="Test Client",
            description="Test client",
            billing_info={}
        )
        db_session.add(client)
        db_session.flush()
        
        project = Project(
            name="Test Project",
            description="Test project",
            start_date=datetime.utcnow(),
            client_id=client.id,
            status=uuid4()
        )
        db_session.add(project)
        db_session.flush()
        
        # Create list entries
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Blood Sample",
            active=True
        )
        status = ListEntry(
            list_id=uuid4(),
            name="Received",
            active=True
        )
        matrix = ListEntry(
            list_id=uuid4(),
            name="Blood",
            active=True
        )
        db_session.add_all([sample_type, status, matrix])
        db_session.flush()
        
        # Create custom attribute config
        config = CustomAttributeConfig(
            id=uuid4(),
            name="ph_level_config",
            entity_type="samples",
            attr_name="ph_level",
            data_type="number",
            validation_rules={"min": 0, "max": 14},
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(config)
        db_session.commit()
        
        return {
            "client": client,
            "project": project,
            "sample_type": sample_type,
            "status": status,
            "matrix": matrix,
            "config": config
        }
    
    def test_create_sample_with_valid_custom_attributes(self, client: TestClient, test_admin_user, test_data):
        """Test creating sample with valid custom attributes"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create sample with custom attributes
        sample_data = {
            "name": "SAMPLE-001",
            "description": "Test sample",
            "due_date": (datetime.utcnow()).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "status": str(test_data["status"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "custom_attributes": {
                "ph_level": 7.0
            }
        }
        
        response = client.post(
            "/samples/",
            json=sample_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["custom_attributes"]["ph_level"] == 7.0
    
    def test_create_sample_with_invalid_custom_attributes(self, client: TestClient, test_admin_user, test_data):
        """Test creating sample with invalid custom attributes fails"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create sample with invalid custom attribute value (out of range)
        sample_data = {
            "name": "SAMPLE-002",
            "description": "Test sample",
            "due_date": (datetime.utcnow()).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "status": str(test_data["status"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "custom_attributes": {
                "ph_level": 15.0  # Out of range (max is 14)
            }
        }
        
        response = client.post(
            "/samples/",
            json=sample_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"]["message"].lower()
    
    def test_create_sample_with_unknown_custom_attribute(self, client: TestClient, test_admin_user, test_data):
        """Test creating sample with unknown custom attribute fails"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create sample with unknown custom attribute
        sample_data = {
            "name": "SAMPLE-003",
            "description": "Test sample",
            "due_date": (datetime.utcnow()).isoformat(),
            "received_date": datetime.utcnow().isoformat(),
            "sample_type": str(test_data["sample_type"].id),
            "status": str(test_data["status"].id),
            "matrix": str(test_data["matrix"].id),
            "project_id": str(test_data["project"].id),
            "custom_attributes": {
                "unknown_attr": "value"
            }
        }
        
        response = client.post(
            "/samples/",
            json=sample_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "unknown custom attribute" in response.json()["detail"]["errors"][0].lower()
    
    def test_update_sample_with_custom_attributes(self, client: TestClient, test_admin_user, test_data, db_session: Session):
        """Test updating sample with custom attributes"""
        # Create sample first
        sample = Sample(
            name="SAMPLE-004",
            description="Test sample",
            received_date=datetime.utcnow(),
            sample_type=test_data["sample_type"].id,
            status=test_data["status"].id,
            matrix=test_data["matrix"].id,
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
        
        # Update sample with custom attributes
        update_data = {
            "custom_attributes": {
                "ph_level": 6.5
            }
        }
        
        response = client.patch(
            f"/samples/{sample.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["custom_attributes"]["ph_level"] == 6.5

