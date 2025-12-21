"""
Tests for aliquots and derivatives API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from models.sample import Sample
from models.container import Container, Contents
from models.container_type import ContainerType
from models.user import User
from models.role import Role
from models.permission import Permission
from models.role_permission import RolePermission

client = TestClient(app)


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
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample type and status
        sample_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=None,  # Will be set later
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        sample_status = ListEntry(
            name="Available for Testing",
            description="Sample available for testing",
            list_id=None,  # Will be set later
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Sample",
            description="Parent sample for aliquot",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=None,
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
            dimensions="12x75",
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
        
        aliquot_data = {
            "parent_sample_id": str(parent_sample.id),
            "name": "Aliquot 1",
            "description": "First aliquot from parent",
            "container_id": str(container.id),
            "concentration": 10.5,
            "amount": 2.0,
            "temperature": 4.0
        }
        
        response = client.post("/aliquots/aliquot", json=aliquot_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Aliquot 1"
        assert data["parent_sample_id"] == str(parent_sample.id)
        assert data["container_id"] == str(container.id)
        assert data["project_id"] == str(project.id)
        assert data["client_id"] == str(client_entity.id)
    
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
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample types and status
        blood_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(blood_type)
        db_session.flush()
        
        dna_type = ListEntry(
            name="DNA",
            description="DNA sample",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(dna_type)
        db_session.flush()
        
        sample_status = ListEntry(
            name="Available for Testing",
            description="Sample available for testing",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Blood Sample",
            description="Parent blood sample for derivative",
            sample_type=blood_type.id,
            status=sample_status.id,
            matrix=None,
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
            dimensions="8x32",
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
        
        response = client.post("/aliquots/derivative", json=derivative_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "DNA Extract"
        assert data["parent_sample_id"] == str(parent_sample.id)
        assert data["sample_type"] == str(dna_type.id)
        assert data["container_id"] == str(container.id)
        assert data["project_id"] == str(project.id)
        assert data["client_id"] == str(client_entity.id)
    
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
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample type and status
        sample_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        sample_status = ListEntry(
            name="Available for Testing",
            description="Sample available for testing",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_status)
        db_session.flush()
        
        # Create samples
        sample1 = Sample(
            name="Sample 1",
            description="First sample for pooling",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=None,
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
            matrix=None,
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
            dimensions="15x100",
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
        
        # Create units
        mg_unit = Unit(
            name="mg",
            description="Milligram",
            type=None,  # Will be set later
            multiplier=0.001,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(mg_unit)
        db_session.flush()
        
        mg_ml_unit = Unit(
            name="mg/mL",
            description="Milligram per milliliter",
            type=None,  # Will be set later
            multiplier=1.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(mg_ml_unit)
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
        assert response.status_code == 200
        
        data = response.json()
        assert data["container_id"] == str(container.id)
        assert len(data["pooled_samples"]) == 2
        assert str(sample1.id) in data["pooled_samples"]
        assert str(sample2.id) in data["pooled_samples"]
        assert data["notes"] == "Pooled samples for testing"
    
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
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample type and status
        sample_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        sample_status = ListEntry(
            name="Available for Testing",
            description="Sample available for testing",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Sample for Get",
            description="Parent sample for getting aliquots",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=None,
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
            dimensions="12x75",
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
        
        # Create aliquots
        aliquot1 = Sample(
            name="Aliquot 1",
            description="First aliquot",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=None,
            parent_sample_id=parent_sample.id,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(aliquot1)
        db_session.flush()
        
        aliquot2 = Sample(
            name="Aliquot 2",
            description="Second aliquot",
            sample_type=sample_type.id,
            status=sample_status.id,
            matrix=None,
            parent_sample_id=parent_sample.id,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(aliquot2)
        db_session.flush()
        
        # Create contents entries
        contents1 = Contents(
            container_id=container1.id,
            sample_id=aliquot1.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(contents1)
        
        contents2 = Contents(
            container_id=container2.id,
            sample_id=aliquot2.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(contents2)
        db_session.commit()
        
        response = client.get(f"/aliquots/parent/{parent_sample.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert any(item["name"] == "Aliquot 1" for item in data)
        assert any(item["name"] == "Aliquot 2" for item in data)
    
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
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample types and status
        blood_type = ListEntry(
            name="Blood",
            description="Blood sample",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(blood_type)
        db_session.flush()
        
        dna_type = ListEntry(
            name="DNA",
            description="DNA sample",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(dna_type)
        db_session.flush()
        
        sample_status = ListEntry(
            name="Available for Testing",
            description="Sample available for testing",
            list_id=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_status)
        db_session.flush()
        
        # Create parent sample
        parent_sample = Sample(
            name="Parent Blood Sample for Get",
            description="Parent blood sample for getting derivatives",
            sample_type=blood_type.id,
            status=sample_status.id,
            matrix=None,
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
            dimensions="8x32",
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
            matrix=None,
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
            matrix=None,
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
            sample_id=derivative1.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(contents1)
        
        contents2 = Contents(
            container_id=container2.id,
            sample_id=derivative2.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(contents2)
        db_session.commit()
        
        response = client.get(f"/aliquots/derivatives/{parent_sample.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert any(item["name"] == "DNA Extract 1" for item in data)
        assert any(item["name"] == "DNA Extract 2" for item in data)
