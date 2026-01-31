"""
Tests for name templates endpoints and name generation
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.name_template import NameTemplate
from models.sample import Sample
from models.project import Project
from models.batch import Batch
from models.analysis import Analysis
from models.container import Container
from models.client import Client
from models.list import List, ListEntry
from app.core.security import create_access_token
from app.core.name_generation import (
    generate_name, generate_name_for_sample, generate_name_for_project,
    generate_name_for_batch, generate_name_for_analysis, generate_name_for_container,
    check_name_uniqueness
)
from datetime import datetime
from uuid import uuid4


class TestNameTemplatesCRUD:
    """Test name templates CRUD operations"""
    
    def test_create_name_template_success(self, client: TestClient, test_admin_user, db_session: Session):
        """Test successful name template creation"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create template
        template_data = {
            "entity_type": "sample",
            "template": "TEST-{YYYY}-{SEQ}",
            "description": "Test template for samples",
            "active": True
        }
        
        response = client.post(
            "/admin/name-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["entity_type"] == "sample"
        assert data["template"] == "TEST-{YYYY}-{SEQ}"
        assert data["active"] is True
        assert data.get("seq_padding_digits", 1) == 1
    
    def test_create_name_template_with_seq_padding_digits(self, client: TestClient, test_admin_user, db_session: Session):
        """Test creating a name template with seq_padding_digits (active=False to avoid conflicting with seed)"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        template_data = {
            "entity_type": "analysis",
            "template": "AN-{YY}-{SEQ}",
            "description": "Analysis with YY and padding",
            "active": False,
            "seq_padding_digits": 3
        }
        response = client.post(
            "/admin/name-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["entity_type"] == "analysis"
        assert data["template"] == "AN-{YY}-{SEQ}"
        assert data["seq_padding_digits"] == 3

    def test_create_name_template_duplicate_active(self, client: TestClient, test_admin_user, db_session: Session):
        """Test that only one active template per entity_type is allowed"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create first active template
        template_data = {
            "entity_type": "sample",
            "template": "TEST-{YYYY}-{SEQ}",
            "active": True
        }
        
        response = client.post(
            "/admin/name-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        
        # Try to create another active template for same entity_type
        response = client.post(
            "/admin/name-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "active template already exists" in response.json()["detail"].lower()
    
    def test_get_name_templates(self, client: TestClient, test_admin_user, db_session: Session):
        """Test listing name templates"""
        # Create test templates
        template1 = NameTemplate(
            id=uuid4(),
            name="test_template_1",
            entity_type="sample",
            template="SAMPLE-{YYYY}-{SEQ}",
            description="Test template 1",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        template2 = NameTemplate(
            id=uuid4(),
            name="test_template_2",
            entity_type="project",
            template="PROJ-{CLIENT}-{SEQ}",
            description="Test template 2",
            active=False,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add_all([template1, template2])
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # List all templates
        response = client.get(
            "/admin/name-templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        templates = data["templates"]
        entity_types = [t["entity_type"] for t in templates]
        assert "sample" in entity_types
        assert "project" in entity_types
    
    def test_get_name_templates_filtered(self, client: TestClient, test_admin_user, db_session: Session):
        """Test filtering name templates by entity_type and active status"""
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Filter by entity_type
        response = client.get(
            "/admin/name-templates?entity_type=sample",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for template in data["templates"]:
            assert template["entity_type"] == "sample"
    
    def test_update_name_template(self, client: TestClient, test_admin_user, db_session: Session):
        """Test updating a name template"""
        # Create template
        template = NameTemplate(
            id=uuid4(),
            name="test_template",
            entity_type="sample",
            template="OLD-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Update template
        update_data = {
            "template": "NEW-{YYYY}-{SEQ}",
            "description": "Updated template"
        }
        
        response = client.patch(
            f"/admin/name-templates/{template.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["template"] == "NEW-{YYYY}-{SEQ}"
        assert data["description"] == "Updated template"
    
    def test_delete_name_template(self, client: TestClient, test_admin_user, db_session: Session):
        """Test soft deleting a name template"""
        # Create template
        template = NameTemplate(
            id=uuid4(),
            name="test_template",
            entity_type="sample",
            template="TEST-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Delete template (soft delete)
        response = client.delete(
            f"/admin/name-templates/{template.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 204
        
        # Verify template is inactive
        db_session.refresh(template)
        assert template.active is False


class TestNameGeneration:
    """Test name generation functionality"""
    
    def test_generate_name_with_template(self, db_session: Session, test_admin_user):
        """Test generating a name using a template"""
        # Create template
        template = NameTemplate(
            id=uuid4(),
            name="test_template",
            entity_type="sample",
            template="TEST-{YYYY}-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Generate name
        name = generate_name(db_session, "sample")
        
        assert name.startswith("TEST-")
        assert str(datetime.now().year) in name
        assert "-" in name
    
    def test_generate_name_without_template(self, db_session: Session):
        """Test generating a name when no template exists (fallback to UUID)"""
        # Generate name without template
        name = generate_name(db_session, "sample")
        
        # Should be a UUID string
        assert len(name) == 36  # UUID string length
        assert name.count("-") == 4  # UUID format
    
    def test_generate_name_uniqueness(self, db_session: Session, test_admin_user):
        """Test that generated names are unique"""
        # Create template
        template = NameTemplate(
            id=uuid4(),
            name="test_template",
            entity_type="sample",
            template="UNIQUE-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Generate multiple names
        name1 = generate_name(db_session, "sample")
        name2 = generate_name(db_session, "sample")
        name3 = generate_name(db_session, "sample")
        
        # All should be unique
        assert name1 != name2
        assert name2 != name3
        assert name1 != name3
    
    def test_generate_name_with_client(self, db_session: Session, test_admin_user):
        """Test generating a name with CLIENT placeholder"""
        # Create client
        client = Client(
            id=uuid4(),
            name="Test Client Inc",
            billing_info={}
        )
        db_session.add(client)
        db_session.flush()
        
        # Create template with CLIENT placeholder
        template = NameTemplate(
            id=uuid4(),
            name="test_template",
            entity_type="project",
            template="PROJ-{CLIENT}-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Generate name with client
        name = generate_name(db_session, "project", client_name=client.name)
        
        assert name.startswith("PROJ-")
        assert "TESTCLIENT" in name or "UNKNOWN" in name
    
    def test_generate_name_for_sample(self, db_session: Session, test_admin_user):
        """Test generating name for sample with project context"""
        # Create client and project
        client = Client(
            id=uuid4(),
            name="Test Client",
            billing_info={}
        )
        db_session.add(client)
        db_session.flush()
        
        status_entry = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Active"
        )
        db_session.add(status_entry)
        db_session.flush()
        
        project = Project(
            id=uuid4(),
            name="Test Project",
            start_date=datetime.now(),
            client_id=client.id,
            status=status_entry.id
        )
        db_session.add(project)
        db_session.commit()
        
        # Create template
        template = NameTemplate(
            id=uuid4(),
            name="sample_template",
            entity_type="sample",
            template="SAMPLE-{YYYY}-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Generate name
        name = generate_name_for_sample(db_session, project_id=project.id)
        
        assert name.startswith("SAMPLE-")
    
    def test_check_name_uniqueness(self, db_session: Session, test_admin_user):
        """Test checking name uniqueness"""
        # Create a sample with a name
        status_entry = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Received"
        )
        db_session.add(status_entry)
        db_session.flush()
        
        sample_type = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Blood"
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Water"
        )
        db_session.add(matrix)
        db_session.flush()
        
        client = Client(
            id=uuid4(),
            name="Test Client",
            billing_info={}
        )
        db_session.add(client)
        db_session.flush()
        
        project = Project(
            id=uuid4(),
            name="Test Project",
            start_date=datetime.now(),
            client_id=client.id,
            status=status_entry.id
        )
        db_session.add(project)
        db_session.flush()
        
        sample = Sample(
            id=uuid4(),
            name="EXISTING-SAMPLE-001",
            sample_type=sample_type.id,
            status=status_entry.id,
            matrix=matrix.id,
            project_id=project.id,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(sample)
        db_session.commit()
        
        # Check uniqueness
        assert check_name_uniqueness(db_session, "sample", "EXISTING-SAMPLE-001") is False
        assert check_name_uniqueness(db_session, "sample", "NEW-SAMPLE-001") is True

    def test_generate_name_with_yy_placeholder(self, db_session: Session, test_admin_user):
        """Test generating a name with {YY} (two-digit year) placeholder"""
        template = NameTemplate(
            id=uuid4(),
            name="test_template",
            entity_type="sample",
            template="S-{YY}-{SEQ}",
            active=True,
            seq_padding_digits=1,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        name = generate_name(db_session, "sample")
        assert name.startswith("S-")
        assert str(datetime.now().year % 100).zfill(2) in name

    def test_generate_name_seq_padding_digits(self, db_session: Session, test_admin_user):
        """Test that {SEQ} is padded to seq_padding_digits"""
        template = NameTemplate(
            id=uuid4(),
            name="test_template",
            entity_type="sample",
            template="PAD-{SEQ}",
            active=True,
            seq_padding_digits=4,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        name = generate_name(db_session, "sample")
        assert name.startswith("PAD-")
        seq_part = name.replace("PAD-", "")
        assert len(seq_part) == 4
        assert seq_part.isdigit()


class TestSequenceStartEndpoint:
    """Test POST /admin/sequences/{entity_type}/start"""

    def test_set_sequence_start_success(self, client: TestClient, test_admin_user, db_session: Session):
        """Test setting sequence start value"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        response = client.post(
            "/admin/sequences/sample/start",
            json={"start_value": 100},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "sample"
        assert data["start_value"] == 100
        assert "restarted" in data["message"].lower() or "100" in data["message"]

    def test_set_sequence_start_invalid_entity_type(self, client: TestClient, test_admin_user):
        """Test that invalid entity_type returns 400"""
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        response = client.post(
            "/admin/sequences/invalid/start",
            json={"start_value": 1},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "entity_type" in response.json()["detail"].lower()

    def test_set_sequence_start_requires_admin(self, client: TestClient):
        """Test that sequence start requires config:edit (admin)"""
        response = client.post(
            "/admin/sequences/sample/start",
            json={"start_value": 1},
        )
        assert response.status_code in (401, 403)


class TestNameGenerationIntegration:
    """Test name generation integration with create endpoints"""
    
    def test_create_sample_without_name(self, client: TestClient, test_admin_user, db_session: Session):
        """Test creating a sample without providing a name (auto-generation)"""
        # Setup: Create necessary data
        client_obj = Client(
            id=uuid4(),
            name="Test Client",
            billing_info={}
        )
        db_session.add(client_obj)
        db_session.flush()
        
        status_entry = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Received"
        )
        db_session.add(status_entry)
        db_session.flush()
        
        sample_type = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Blood"
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Water"
        )
        db_session.add(matrix)
        db_session.flush()
        
        project = Project(
            id=uuid4(),
            name="Test Project",
            start_date=datetime.now(),
            client_id=client_obj.id,
            status=status_entry.id
        )
        db_session.add(project)
        db_session.commit()
        
        # Create template
        template = NameTemplate(
            id=uuid4(),
            name="sample_template",
            entity_type="sample",
            template="AUTO-{YYYY}-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create sample without name
        sample_data = {
            "sample_type": str(sample_type.id),
            "status": str(status_entry.id),
            "matrix": str(matrix.id),
            "project_id": str(project.id),
            "received_date": datetime.now().isoformat()
        }
        
        response = client.post(
            "/samples",
            json=sample_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"].startswith("AUTO-")
    
    def test_create_batch_without_name(self, client: TestClient, test_admin_user, db_session: Session):
        """Test creating a batch without providing a name (auto-generation)"""
        # Setup: Create necessary data
        status_entry = ListEntry(
            id=uuid4(),
            list_id=uuid4(),
            name="Created"
        )
        db_session.add(status_entry)
        db_session.commit()
        
        # Create template
        template = NameTemplate(
            id=uuid4(),
            name="batch_template",
            entity_type="batch",
            template="BATCH-{YYYYMMDD}-{SEQ}",
            active=True,
            created_by=test_admin_user.id,
            modified_by=test_admin_user.id
        )
        db_session.add(template)
        db_session.commit()
        
        # Get auth token
        auth_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpassword"}
        )
        token = auth_response.json()["access_token"]
        
        # Create batch without name
        batch_data = {
            "status": str(status_entry.id)
        }
        
        response = client.post(
            "/batches",
            json=batch_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"].startswith("BATCH-")

