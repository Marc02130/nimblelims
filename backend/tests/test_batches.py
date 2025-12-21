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
