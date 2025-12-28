"""
Tests for batches API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from models.batch import Batch
from models.container import Container
from models.user import User
from models.role import Role
from models.permission import Permission
from models.role_permission import RolePermission
from datetime import datetime
from uuid import uuid4

client = TestClient(app)


class TestBatchesAPI:
    """Test batches API endpoints"""
    
    def test_create_batch(self, db_session, auth_headers, sample_user):
        """Test creating a new batch"""
        from models.list import ListEntry
        
        # Get a status for the batch
        status = db_session.query(ListEntry).filter(
            ListEntry.name == "Created"
        ).first()
        
        if not status:
            # Create a status if it doesn't exist
            from models.list import List
            batch_status_list = db_session.query(List).filter(
                List.name == "batch_status"
            ).first()
            
            if not batch_status_list:
                batch_status_list = List(
                    name="batch_status",
                    description="Batch status list",
                    created_by=sample_user.id,
                    modified_by=sample_user.id
                )
                db_session.add(batch_status_list)
                db_session.flush()
            
            status = ListEntry(
                name="Created",
                description="Batch created",
                list_id=batch_status_list.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(status)
            db_session.commit()
        
        batch_data = {
            "name": "Test Batch 1",
            "description": "Test batch for API testing",
            "status": str(status.id),
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-02T00:00:00Z"
        }
        
        response = client.post("/batches/", json=batch_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Test Batch 1"
        assert data["description"] == "Test batch for API testing"
        assert data["status"] == str(status.id)
    
    def test_create_batch_with_containers(self, db_session, auth_headers, sample_user):
        """Test creating a batch with containers"""
        from models.list import ListEntry
        from models.container_type import ContainerType
        
        # Get a status for the batch
        status = db_session.query(ListEntry).filter(
            ListEntry.name == "Created"
        ).first()
        
        if not status:
            # Create status as in previous test
            from models.list import List
            batch_status_list = db_session.query(List).filter(
                List.name == "batch_status"
            ).first()
            
            if not batch_status_list:
                batch_status_list = List(
                    name="batch_status",
                    description="Batch status list",
                    created_by=sample_user.id,
                    modified_by=sample_user.id
                )
                db_session.add(batch_status_list)
                db_session.flush()
            
            status = ListEntry(
                name="Created",
                description="Batch created",
                list_id=batch_status_list.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(status)
            db_session.commit()
        
        # Create a container type
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
            name="Container 1",
            description="Test container 1",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        
        container2 = Container(
            name="Container 2",
            description="Test container 2",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container2)
        db_session.commit()
        
        batch_data = {
            "name": "Test Batch with Containers",
            "description": "Test batch with containers",
            "status": str(status.id),
            "containers": [
                {
                    "container_id": str(container1.id),
                    "position": "A1",
                    "notes": "First container"
                },
                {
                    "container_id": str(container2.id),
                    "position": "A2",
                    "notes": "Second container"
                }
            ]
        }
        
        response = client.post("/batches/with-containers", json=batch_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Test Batch with Containers"
        assert data["status"] == str(status.id)
    
    def test_get_batches(self, db_session, auth_headers, sample_user):
        """Test getting batches list"""
        # Create a test batch
        from models.list import ListEntry
        
        status = db_session.query(ListEntry).filter(
            ListEntry.name == "Created"
        ).first()
        
        if not status:
            # Create status as in previous tests
            from models.list import List
            batch_status_list = db_session.query(List).filter(
                List.name == "batch_status"
            ).first()
            
            if not batch_status_list:
                batch_status_list = List(
                    name="batch_status",
                    description="Batch status list",
                    created_by=sample_user.id,
                    modified_by=sample_user.id
                )
                db_session.add(batch_status_list)
                db_session.flush()
            
            status = ListEntry(
                name="Created",
                description="Batch created",
                list_id=batch_status_list.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(status)
            db_session.commit()
        
        batch = Batch(
            name="Test Batch for List",
            description="Test batch for listing",
            status=status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(batch)
        db_session.commit()
        
        response = client.get("/batches/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "batches" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["batches"]) >= 1
    
    def test_get_batch_by_id(self, db_session, auth_headers, sample_user):
        """Test getting a specific batch by ID"""
        from models.list import ListEntry
        
        status = db_session.query(ListEntry).filter(
            ListEntry.name == "Created"
        ).first()
        
        if not status:
            # Create status as in previous tests
            from models.list import List
            batch_status_list = db_session.query(List).filter(
                List.name == "batch_status"
            ).first()
            
            if not batch_status_list:
                batch_status_list = List(
                    name="batch_status",
                    description="Batch status list",
                    created_by=sample_user.id,
                    modified_by=sample_user.id
                )
                db_session.add(batch_status_list)
                db_session.flush()
            
            status = ListEntry(
                name="Created",
                description="Batch created",
                list_id=batch_status_list.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(status)
            db_session.commit()
        
        batch = Batch(
            name="Test Batch for Get",
            description="Test batch for getting by ID",
            status=status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(batch)
        db_session.commit()
        
        response = client.get(f"/batches/{batch.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(batch.id)
        assert data["name"] == "Test Batch for Get"
    
    def test_update_batch(self, db_session, auth_headers, sample_user):
        """Test updating a batch"""
        from models.list import ListEntry
        
        status = db_session.query(ListEntry).filter(
            ListEntry.name == "Created"
        ).first()
        
        if not status:
            # Create status as in previous tests
            from models.list import List
            batch_status_list = db_session.query(List).filter(
                List.name == "batch_status"
            ).first()
            
            if not batch_status_list:
                batch_status_list = List(
                    name="batch_status",
                    description="Batch status list",
                    created_by=sample_user.id,
                    modified_by=sample_user.id
                )
                db_session.add(batch_status_list)
                db_session.flush()
            
            status = ListEntry(
                name="Created",
                description="Batch created",
                list_id=batch_status_list.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(status)
            db_session.commit()
        
        batch = Batch(
            name="Test Batch for Update",
            description="Test batch for updating",
            status=status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(batch)
        db_session.commit()
        
        update_data = {
            "name": "Updated Batch Name",
            "description": "Updated batch description"
        }
        
        response = client.patch(f"/batches/{batch.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Updated Batch Name"
        assert data["description"] == "Updated batch description"
    
    def test_delete_batch(self, db_session, auth_headers, sample_user):
        """Test deleting a batch"""
        from models.list import ListEntry
        
        status = db_session.query(ListEntry).filter(
            ListEntry.name == "Created"
        ).first()
        
        if not status:
            # Create status as in previous tests
            from models.list import List
            batch_status_list = db_session.query(List).filter(
                List.name == "batch_status"
            ).first()
            
            if not batch_status_list:
                batch_status_list = List(
                    name="batch_status",
                    description="Batch status list",
                    created_by=sample_user.id,
                    modified_by=sample_user.id
                )
                db_session.add(batch_status_list)
                db_session.flush()
            
            status = ListEntry(
                name="Created",
                description="Batch created",
                list_id=batch_status_list.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(status)
            db_session.commit()
        
        batch = Batch(
            name="Test Batch for Delete",
            description="Test batch for deletion",
            status=status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(batch)
        db_session.commit()
        
        response = client.delete(f"/batches/{batch.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Batch deleted successfully"
        
        # Verify batch is soft deleted
        db_session.refresh(batch)
        assert batch.active == False

    def test_create_cross_project_batch_success(self, db_session, auth_headers, sample_user):
        """Test creating a cross-project batch with compatible samples"""
        from models.list import ListEntry, List
        from models.container_type import ContainerType
        from models.container import Container, Contents
        from models.sample import Sample
        from models.project import Project
        from models.client import Client
        from models.test import Test
        from models.analysis import Analysis
        from models.project import ProjectUser
        
        # Create two clients and projects
        client1 = Client(
            name="Client 1",
            description="Test client 1",
            billing_info={}
        )
        db_session.add(client1)
        db_session.flush()
        
        client2 = Client(
            name="Client 2",
            description="Test client 2",
            billing_info={}
        )
        db_session.add(client2)
        db_session.flush()
        
        project1 = Project(
            name="Project 1",
            description="Test project 1",
            start_date=datetime.utcnow(),
            client_id=client1.id,
            status=uuid4()
        )
        db_session.add(project1)
        db_session.flush()
        
        project2 = Project(
            name="Project 2",
            description="Test project 2",
            start_date=datetime.utcnow(),
            client_id=client2.id,
            status=uuid4()
        )
        db_session.add(project2)
        db_session.flush()
        
        # Grant user access to both projects
        project_user1 = ProjectUser(
            project_id=project1.id,
            user_id=sample_user.id,
            granted_by=sample_user.id
        )
        db_session.add(project_user1)
        
        project_user2 = ProjectUser(
            project_id=project2.id,
            user_id=sample_user.id,
            granted_by=sample_user.id
        )
        db_session.add(project_user2)
        db_session.flush()
        
        # Create shared analysis (prep method)
        prep_analysis = Analysis(
            name="EPA Method 8080 Prep",
            description="Shared prep analysis",
            method="EPA Method 8080",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(prep_analysis)
        db_session.flush()
        
        # Create batch status
        batch_status_list = db_session.query(List).filter(
            List.name == "batch_status"
        ).first()
        
        if not batch_status_list:
            batch_status_list = List(
                name="batch_status",
                description="Batch status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(batch_status_list)
            db_session.flush()
        
        status = ListEntry(
            name="Created",
            description="Batch created",
            list_id=batch_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(status)
        db_session.flush()
        
        # Create sample type and matrix
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Water",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix)
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
            name="Container 1",
            description="Test container 1",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        db_session.flush()
        
        container2 = Container(
            name="Container 2",
            description="Test container 2",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container2)
        db_session.flush()
        
        # Create samples in different projects
        sample1 = Sample(
            name="SAMPLE-001",
            description="Sample from project 1",
            project_id=project1.id,
            sample_type=sample_type.id,
            status=uuid4(),
            matrix=matrix.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample1)
        db_session.flush()
        
        sample2 = Sample(
            name="SAMPLE-002",
            description="Sample from project 2",
            project_id=project2.id,
            sample_type=sample_type.id,
            status=uuid4(),
            matrix=matrix.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample2)
        db_session.flush()
        
        # Link samples to containers
        contents1 = Contents(
            container_id=container1.id,
            sample_id=sample1.id
        )
        db_session.add(contents1)
        
        contents2 = Contents(
            container_id=container2.id,
            sample_id=sample2.id
        )
        db_session.add(contents2)
        db_session.flush()
        
        # Create tests with shared analysis
        test1 = Test(
            sample_id=sample1.id,
            analysis_id=prep_analysis.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test1)
        
        test2 = Test(
            sample_id=sample2.id,
            analysis_id=prep_analysis.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test2)
        db_session.commit()
        
        # Create cross-project batch
        batch_data = {
            "name": "Cross-Project Batch",
            "description": "Batch with samples from multiple projects",
            "status": str(status.id),
            "container_ids": [str(container1.id), str(container2.id)],
            "cross_project": True
        }
        
        response = client.post("/batches/", json=batch_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Cross-Project Batch"
        assert "containers" in data
        assert len(data["containers"]) == 2
    
    def test_create_cross_project_batch_incompatible(self, db_session, auth_headers, sample_user):
        """Test creating a cross-project batch with incompatible samples (no shared analysis)"""
        from models.list import ListEntry, List
        from models.container_type import ContainerType
        from models.container import Container, Contents
        from models.sample import Sample
        from models.project import Project
        from models.client import Client
        from models.test import Test
        from models.analysis import Analysis
        from models.project import ProjectUser
        
        # Create two clients and projects
        client1 = Client(
            name="Client 1",
            description="Test client 1",
            billing_info={}
        )
        db_session.add(client1)
        db_session.flush()
        
        client2 = Client(
            name="Client 2",
            description="Test client 2",
            billing_info={}
        )
        db_session.add(client2)
        db_session.flush()
        
        project1 = Project(
            name="Project 1",
            description="Test project 1",
            start_date=datetime.utcnow(),
            client_id=client1.id,
            status=uuid4()
        )
        db_session.add(project1)
        db_session.flush()
        
        project2 = Project(
            name="Project 2",
            description="Test project 2",
            start_date=datetime.utcnow(),
            client_id=client2.id,
            status=uuid4()
        )
        db_session.add(project2)
        db_session.flush()
        
        # Grant user access to both projects
        project_user1 = ProjectUser(
            project_id=project1.id,
            user_id=sample_user.id,
            granted_by=sample_user.id
        )
        db_session.add(project_user1)
        
        project_user2 = ProjectUser(
            project_id=project2.id,
            user_id=sample_user.id,
            granted_by=sample_user.id
        )
        db_session.add(project_user2)
        db_session.flush()
        
        # Create different analyses (no shared analysis)
        analysis1 = Analysis(
            name="Analysis 1",
            description="Analysis for project 1",
            method="Method 1",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis1)
        db_session.flush()
        
        analysis2 = Analysis(
            name="Analysis 2",
            description="Analysis for project 2",
            method="Method 2",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis2)
        db_session.flush()
        
        # Create batch status
        batch_status_list = db_session.query(List).filter(
            List.name == "batch_status"
        ).first()
        
        if not batch_status_list:
            batch_status_list = List(
                name="batch_status",
                description="Batch status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(batch_status_list)
            db_session.flush()
        
        status = ListEntry(
            name="Created",
            description="Batch created",
            list_id=batch_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(status)
        db_session.flush()
        
        # Create sample type and matrix
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Water",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix)
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
            name="Container 1",
            description="Test container 1",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        db_session.flush()
        
        container2 = Container(
            name="Container 2",
            description="Test container 2",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container2)
        db_session.flush()
        
        # Create samples in different projects
        sample1 = Sample(
            name="SAMPLE-001",
            description="Sample from project 1",
            project_id=project1.id,
            sample_type=sample_type.id,
            status=uuid4(),
            matrix=matrix.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample1)
        db_session.flush()
        
        sample2 = Sample(
            name="SAMPLE-002",
            description="Sample from project 2",
            project_id=project2.id,
            sample_type=sample_type.id,
            status=uuid4(),
            matrix=matrix.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample2)
        db_session.flush()
        
        # Link samples to containers
        contents1 = Contents(
            container_id=container1.id,
            sample_id=sample1.id
        )
        db_session.add(contents1)
        
        contents2 = Contents(
            container_id=container2.id,
            sample_id=sample2.id
        )
        db_session.add(contents2)
        db_session.flush()
        
        # Create tests with different analyses (no shared analysis)
        test1 = Test(
            sample_id=sample1.id,
            analysis_id=analysis1.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test1)
        
        test2 = Test(
            sample_id=sample2.id,
            analysis_id=analysis2.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test2)
        db_session.commit()
        
        # Try to create cross-project batch (should fail - incompatible)
        batch_data = {
            "name": "Incompatible Batch",
            "description": "Batch with incompatible samples",
            "status": str(status.id),
            "container_ids": [str(container1.id), str(container2.id)],
            "cross_project": True
        }
        
        response = client.post("/batches/", json=batch_data, headers=auth_headers)
        assert response.status_code == 400
        assert "incompatible" in response.json()["detail"].lower() or "shared" in response.json()["detail"].lower()
    
    def test_create_cross_project_batch_rls_denial(self, db_session, auth_headers, sample_user):
        """Test creating a cross-project batch with RLS denial (user lacks access to one project)"""
        from models.list import ListEntry, List
        from models.container_type import ContainerType
        from models.container import Container, Contents
        from models.sample import Sample
        from models.project import Project
        from models.client import Client
        from models.test import Test
        from models.analysis import Analysis
        
        # Create two clients and projects
        client1 = Client(
            name="Client 1",
            description="Test client 1",
            billing_info={}
        )
        db_session.add(client1)
        db_session.flush()
        
        client2 = Client(
            name="Client 2",
            description="Test client 2",
            billing_info={}
        )
        db_session.add(client2)
        db_session.flush()
        
        project1 = Project(
            name="Project 1",
            description="Test project 1",
            start_date=datetime.utcnow(),
            client_id=client1.id,
            status=uuid4()
        )
        db_session.add(project1)
        db_session.flush()
        
        project2 = Project(
            name="Project 2",
            description="Test project 2",
            start_date=datetime.utcnow(),
            client_id=client2.id,
            status=uuid4()
        )
        db_session.add(project2)
        db_session.flush()
        
        # Grant user access to only project1 (NOT project2)
        project_user1 = ProjectUser(
            project_id=project1.id,
            user_id=sample_user.id,
            granted_by=sample_user.id
        )
        db_session.add(project_user1)
        db_session.flush()
        
        # Create shared analysis
        prep_analysis = Analysis(
            name="EPA Method 8080 Prep",
            description="Shared prep analysis",
            method="EPA Method 8080",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(prep_analysis)
        db_session.flush()
        
        # Create batch status
        batch_status_list = db_session.query(List).filter(
            List.name == "batch_status"
        ).first()
        
        if not batch_status_list:
            batch_status_list = List(
                name="batch_status",
                description="Batch status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(batch_status_list)
            db_session.flush()
        
        status = ListEntry(
            name="Created",
            description="Batch created",
            list_id=batch_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(status)
        db_session.flush()
        
        # Create sample type and matrix
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Water",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix)
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
            name="Container 1",
            description="Test container 1",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        db_session.flush()
        
        container2 = Container(
            name="Container 2",
            description="Test container 2",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container2)
        db_session.flush()
        
        # Create samples in different projects
        sample1 = Sample(
            name="SAMPLE-001",
            description="Sample from project 1",
            project_id=project1.id,
            sample_type=sample_type.id,
            status=uuid4(),
            matrix=matrix.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample1)
        db_session.flush()
        
        sample2 = Sample(
            name="SAMPLE-002",
            description="Sample from project 2",
            project_id=project2.id,
            sample_type=sample_type.id,
            status=uuid4(),
            matrix=matrix.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample2)
        db_session.flush()
        
        # Link samples to containers
        contents1 = Contents(
            container_id=container1.id,
            sample_id=sample1.id
        )
        db_session.add(contents1)
        
        contents2 = Contents(
            container_id=container2.id,
            sample_id=sample2.id
        )
        db_session.add(contents2)
        db_session.flush()
        
        # Create tests with shared analysis
        test1 = Test(
            sample_id=sample1.id,
            analysis_id=prep_analysis.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test1)
        
        test2 = Test(
            sample_id=sample2.id,
            analysis_id=prep_analysis.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test2)
        db_session.commit()
        
        # Try to create cross-project batch (should fail - RLS denial)
        batch_data = {
            "name": "RLS Denied Batch",
            "description": "Batch with RLS denial",
            "status": str(status.id),
            "container_ids": [str(container1.id), str(container2.id)],
            "cross_project": True
        }
        
        response = client.post("/batches/", json=batch_data, headers=auth_headers)
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower() or "permissions" in response.json()["detail"].lower()
    
    def test_create_batch_with_qc_samples(self, db_session, auth_headers, sample_user):
        """Test creating a batch with QC samples (US-27)"""
        from models.list import ListEntry, List
        from models.container_type import ContainerType
        from models.container import Container, Contents
        from models.sample import Sample
        from models.project import Project
        from models.client import Client
        from models.test import Test
        from models.analysis import Analysis
        
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
        
        # Create batch status
        batch_status_list = db_session.query(List).filter(
            List.name == "batch_status"
        ).first()
        
        if not batch_status_list:
            batch_status_list = List(
                name="batch_status",
                description="Batch status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(batch_status_list)
            db_session.flush()
        
        status = ListEntry(
            name="Created",
            description="Batch created",
            list_id=batch_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(status)
        db_session.flush()
        
        # Create sample status list
        sample_status_list = db_session.query(List).filter(
            List.name == "sample_status"
        ).first()
        
        if not sample_status_list:
            sample_status_list = List(
                name="sample_status",
                description="Sample status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(sample_status_list)
            db_session.flush()
        
        received_status = ListEntry(
            name="Received",
            description="Sample received",
            list_id=sample_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(received_status)
        db_session.flush()
        
        # Create QC types list
        qc_types_list = db_session.query(List).filter(
            List.name == "qc_types"
        ).first()
        
        if not qc_types_list:
            qc_types_list = List(
                name="qc_types",
                description="QC types list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(qc_types_list)
            db_session.flush()
        
        blank_qc_type = ListEntry(
            name="Blank",
            description="Blank QC sample",
            list_id=qc_types_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(blank_qc_type)
        db_session.flush()
        
        # Create sample type and matrix
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Water",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix)
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
        
        # Create container and sample
        container = Container(
            name="Container 1",
            description="Test container",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        sample = Sample(
            name="SAMPLE-001",
            description="Test sample",
            project_id=project.id,
            sample_type=sample_type.id,
            status=received_status.id,
            matrix=matrix.id,
            temperature=25.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Link sample to container
        contents = Contents(
            container_id=container.id,
            sample_id=sample.id
        )
        db_session.add(contents)
        db_session.commit()
        
        # Create batch with QC samples
        batch_data = {
            "name": "Batch with QC",
            "description": "Batch with QC samples",
            "status": str(status.id),
            "container_ids": [str(container.id)],
            "qc_additions": [
                {
                    "qc_type": str(blank_qc_type.id),
                    "notes": "QC sample for validation"
                }
            ]
        }
        
        response = client.post("/batches/", json=batch_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Batch with QC"
        assert "containers" in data
        # Should have original container + QC container
        assert len(data["containers"]) >= 2
        
        # Verify QC sample was created
        qc_samples = db_session.query(Sample).filter(
            Sample.name.like("QC-%"),
            Sample.qc_type == blank_qc_type.id
        ).all()
        assert len(qc_samples) == 1
        assert qc_samples[0].project_id == project.id
        assert qc_samples[0].sample_type == sample_type.id
        assert qc_samples[0].matrix == matrix.id
    
    def test_create_batch_qc_requirement_enforcement(self, db_session, auth_headers, sample_user, monkeypatch):
        """Test QC requirement enforcement for specific batch types (US-27)"""
        from models.list import ListEntry, List
        from models.container_type import ContainerType
        from models.container import Container, Contents
        from models.sample import Sample
        from models.project import Project
        from models.client import Client
        
        # Set environment variable to require QC for a specific batch type
        batch_type_id = uuid4()
        monkeypatch.setenv("REQUIRE_QC_FOR_BATCH_TYPES", str(batch_type_id))
        
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
        
        # Create batch status
        batch_status_list = db_session.query(List).filter(
            List.name == "batch_status"
        ).first()
        
        if not batch_status_list:
            batch_status_list = List(
                name="batch_status",
                description="Batch status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(batch_status_list)
            db_session.flush()
        
        status = ListEntry(
            name="Created",
            description="Batch created",
            list_id=batch_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(status)
        db_session.flush()
        
        # Create sample status
        sample_status_list = db_session.query(List).filter(
            List.name == "sample_status"
        ).first()
        
        if not sample_status_list:
            sample_status_list = List(
                name="sample_status",
                description="Sample status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(sample_status_list)
            db_session.flush()
        
        received_status = ListEntry(
            name="Received",
            description="Sample received",
            list_id=sample_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(received_status)
        db_session.flush()
        
        # Create sample type and matrix
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Water",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix)
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
        
        # Create container and sample
        container = Container(
            name="Container 1",
            description="Test container",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container)
        db_session.flush()
        
        sample = Sample(
            name="SAMPLE-001",
            description="Test sample",
            project_id=project.id,
            sample_type=sample_type.id,
            status=received_status.id,
            matrix=matrix.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Link sample to container
        contents = Contents(
            container_id=container.id,
            sample_id=sample.id
        )
        db_session.add(contents)
        db_session.commit()
        
        # Try to create batch without QC (should fail)
        batch_data = {
            "name": "Batch without QC",
            "description": "Batch without QC samples",
            "type": str(batch_type_id),
            "status": str(status.id),
            "container_ids": [str(container.id)]
        }
        
        response = client.post("/batches/", json=batch_data, headers=auth_headers)
        assert response.status_code == 400
        assert "qc" in response.json()["detail"].lower() or "required" in response.json()["detail"].lower()
        
        # Create batch with QC (should succeed)
        qc_types_list = db_session.query(List).filter(
            List.name == "qc_types"
        ).first()
        
        if not qc_types_list:
            qc_types_list = List(
                name="qc_types",
                description="QC types list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(qc_types_list)
            db_session.flush()
        
        blank_qc_type = ListEntry(
            name="Blank",
            description="Blank QC sample",
            list_id=qc_types_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(blank_qc_type)
        db_session.commit()
        
        batch_data_with_qc = {
            "name": "Batch with QC",
            "description": "Batch with QC samples",
            "type": str(batch_type_id),
            "status": str(status.id),
            "container_ids": [str(container.id)],
            "qc_additions": [
                {
                    "qc_type": str(blank_qc_type.id)
                }
            ]
        }
        
        response = client.post("/batches/", json=batch_data_with_qc, headers=auth_headers)
        assert response.status_code == 200
    
    def test_create_cross_project_batch_with_qc_end_to_end(self, db_session, auth_headers, sample_user):
        """End-to-end test: Create cross-project batch with QC samples (Sprint 6 integration)"""
        from models.list import ListEntry, List
        from models.container_type import ContainerType
        from models.container import Container, Contents
        from models.sample import Sample
        from models.project import Project
        from models.client import Client
        from models.test import Test
        from models.analysis import Analysis
        from models.project import ProjectUser
        from models.batch import Batch, BatchContainer
        
        # Create two clients and projects
        client1 = Client(
            name="Client 1",
            description="Test client 1",
            billing_info={}
        )
        db_session.add(client1)
        db_session.flush()
        
        client2 = Client(
            name="Client 2",
            description="Test client 2",
            billing_info={}
        )
        db_session.add(client2)
        db_session.flush()
        
        project1 = Project(
            name="Project 1",
            description="Test project 1",
            start_date=datetime.utcnow(),
            client_id=client1.id,
            status=uuid4()
        )
        db_session.add(project1)
        db_session.flush()
        
        project2 = Project(
            name="Project 2",
            description="Test project 2",
            start_date=datetime.utcnow(),
            client_id=client2.id,
            status=uuid4()
        )
        db_session.add(project2)
        db_session.flush()
        
        # Grant user access to both projects
        project_user1 = ProjectUser(
            project_id=project1.id,
            user_id=sample_user.id,
            granted_by=sample_user.id
        )
        db_session.add(project_user1)
        
        project_user2 = ProjectUser(
            project_id=project2.id,
            user_id=sample_user.id,
            granted_by=sample_user.id
        )
        db_session.add(project_user2)
        db_session.flush()
        
        # Create shared analysis for compatibility
        prep_analysis = Analysis(
            name="EPA Method 8080 Prep",
            description="Shared prep analysis",
            method="EPA Method 8080",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(prep_analysis)
        db_session.flush()
        
        # Create batch status
        batch_status_list = db_session.query(List).filter(
            List.name == "batch_status"
        ).first()
        
        if not batch_status_list:
            batch_status_list = List(
                name="batch_status",
                description="Batch status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(batch_status_list)
            db_session.flush()
        
        status = ListEntry(
            name="Created",
            description="Batch created",
            list_id=batch_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(status)
        db_session.flush()
        
        # Create sample status list
        sample_status_list = db_session.query(List).filter(
            List.name == "sample_status"
        ).first()
        
        if not sample_status_list:
            sample_status_list = List(
                name="sample_status",
                description="Sample status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(sample_status_list)
            db_session.flush()
        
        received_status = ListEntry(
            name="Received",
            description="Sample received",
            list_id=sample_status_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(received_status)
        db_session.flush()
        
        # Create QC types list
        qc_types_list = db_session.query(List).filter(
            List.name == "qc_types"
        ).first()
        
        if not qc_types_list:
            qc_types_list = List(
                name="qc_types",
                description="QC types list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(qc_types_list)
            db_session.flush()
        
        blank_qc_type = ListEntry(
            name="Blank",
            description="Blank QC sample",
            list_id=qc_types_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(blank_qc_type)
        
        matrix_spike_qc_type = ListEntry(
            name="Matrix Spike",
            description="Matrix spike QC sample",
            list_id=qc_types_list.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix_spike_qc_type)
        db_session.flush()
        
        # Create sample type and matrix
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Water",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix)
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
            name="Container 1",
            description="Test container 1",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        db_session.flush()
        
        container2 = Container(
            name="Container 2",
            description="Test container 2",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container2)
        db_session.flush()
        
        # Create samples in different projects
        sample1 = Sample(
            name="SAMPLE-001",
            description="Sample from project 1",
            project_id=project1.id,
            sample_type=sample_type.id,
            status=received_status.id,
            matrix=matrix.id,
            temperature=25.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample1)
        db_session.flush()
        
        sample2 = Sample(
            name="SAMPLE-002",
            description="Sample from project 2",
            project_id=project2.id,
            sample_type=sample_type.id,
            status=received_status.id,
            matrix=matrix.id,
            temperature=25.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample2)
        db_session.flush()
        
        # Link samples to containers
        contents1 = Contents(
            container_id=container1.id,
            sample_id=sample1.id
        )
        db_session.add(contents1)
        
        contents2 = Contents(
            container_id=container2.id,
            sample_id=sample2.id
        )
        db_session.add(contents2)
        db_session.flush()
        
        # Create tests with shared analysis
        test1 = Test(
            sample_id=sample1.id,
            analysis_id=prep_analysis.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test1)
        
        test2 = Test(
            sample_id=sample2.id,
            analysis_id=prep_analysis.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test2)
        db_session.commit()
        
        # Create cross-project batch with QC samples
        batch_data = {
            "name": "Cross-Project Batch with QC",
            "description": "End-to-end test: cross-project batch with QC",
            "status": str(status.id),
            "container_ids": [str(container1.id), str(container2.id)],
            "cross_project": True,
            "qc_additions": [
                {
                    "qc_type": str(blank_qc_type.id),
                    "notes": "Blank QC for cross-project batch"
                },
                {
                    "qc_type": str(matrix_spike_qc_type.id),
                    "notes": "Matrix spike QC for validation"
                }
            ]
        }
        
        response = client.post("/batches/", json=batch_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Cross-Project Batch with QC"
        assert "containers" in data
        
        # Should have 2 original containers + 2 QC containers = 4 total
        assert len(data["containers"]) == 4
        
        # Verify batch was created
        batch = db_session.query(Batch).filter(
            Batch.id == UUID(data["id"])
        ).first()
        assert batch is not None
        assert batch.name == "Cross-Project Batch with QC"
        
        # Verify all containers are linked to batch
        batch_containers = db_session.query(BatchContainer).filter(
            BatchContainer.batch_id == batch.id
        ).all()
        assert len(batch_containers) == 4
        
        # Verify QC samples were created
        qc_samples = db_session.query(Sample).filter(
            Sample.name.like("QC-%"),
            Sample.qc_type.in_([blank_qc_type.id, matrix_spike_qc_type.id])
        ).all()
        assert len(qc_samples) == 2
        
        # Verify QC samples inherit properties from first sample
        for qc_sample in qc_samples:
            assert qc_sample.project_id == project1.id  # Inherited from first sample
            assert qc_sample.sample_type == sample_type.id
            assert qc_sample.matrix == matrix.id
            assert qc_sample.temperature == 25.0
        
        # Verify QC containers were created
        qc_containers = db_session.query(Container).filter(
            Container.name.like("QC-%")
        ).all()
        assert len(qc_containers) == 2
        
        # Verify QC samples are linked to QC containers via Contents
        for qc_sample in qc_samples:
            qc_contents = db_session.query(Contents).filter(
                Contents.sample_id == qc_sample.id
            ).first()
            assert qc_contents is not None
            assert qc_contents.container_id in [c.id for c in qc_containers]
        
        # Verify QC containers are linked to batch
        for qc_container in qc_containers:
            qc_batch_container = db_session.query(BatchContainer).filter(
                BatchContainer.batch_id == batch.id,
                BatchContainer.container_id == qc_container.id
            ).first()
            assert qc_batch_container is not None