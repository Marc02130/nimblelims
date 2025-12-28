"""
Tests for client projects API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from models.client import ClientProject, Client
from models.user import User
from models.role import Role
from models.permission import Permission
from models.role_permission import RolePermission
from app.core.security import get_password_hash

client = TestClient(app)


@pytest.fixture
def sample_user(db_session):
    """Create a sample user with project:manage permission"""
    # Create test role
    test_role = Role(
        name="test_role_project",
        description="Test role with project:manage"
    )
    db_session.add(test_role)
    db_session.flush()
    
    # Create project:manage permission
    project_manage_perm = Permission(
        name="project:manage",
        description="Manage projects"
    )
    db_session.add(project_manage_perm)
    db_session.flush()
    
    # Assign permission to role
    role_perm = RolePermission(role_id=test_role.id, permission_id=project_manage_perm.id)
    db_session.add(role_perm)
    
    # Create test user
    test_user = User(
        name="Sample User",
        username="sampleuser",
        email="sample@example.com",
        password_hash=get_password_hash("samplepassword"),
        role_id=test_role.id
    )
    db_session.add(test_user)
    db_session.commit()
    
    return test_user


@pytest.fixture
def auth_headers(client, sample_user):
    """Get authentication headers for sample user"""
    # Login to get token
    login_response = client.post(
        "/auth/login",
        json={"username": "sampleuser", "password": "samplepassword"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestClientProjectsAPI:
    """Test client projects API endpoints"""
    
    def test_create_client_project(self, db_session, auth_headers, sample_user):
        """Test creating a new client project"""
        # Create a client first
        test_client = Client(
            name="Test Client",
            description="Test client for client projects",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        client_project_data = {
            "name": "Test Client Project",
            "description": "Test client project for API testing",
            "client_id": str(test_client.id)
        }
        
        response = client.post("/client-projects/", json=client_project_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "Test Client Project"
        assert data["description"] == "Test client project for API testing"
        assert data["client_id"] == str(test_client.id)
        assert data["active"] == True
        assert data["created_by"] == str(sample_user.id)
    
    def test_create_client_project_duplicate_name(self, db_session, auth_headers, sample_user):
        """Test creating a client project with duplicate name fails"""
        # Create a client first
        test_client = Client(
            name="Test Client 2",
            description="Test client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        # Create first client project
        client_project = ClientProject(
            name="Duplicate Test Project",
            description="First project",
            client_id=test_client.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        
        # Try to create another with same name
        client_project_data = {
            "name": "Duplicate Test Project",
            "description": "Second project",
            "client_id": str(test_client.id)
        }
        
        response = client.post("/client-projects/", json=client_project_data, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_create_client_project_invalid_client(self, db_session, auth_headers):
        """Test creating a client project with invalid client_id fails"""
        from uuid import uuid4
        
        client_project_data = {
            "name": "Test Project",
            "description": "Test project",
            "client_id": str(uuid4())  # Non-existent client ID
        }
        
        response = client.post("/client-projects/", json=client_project_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Client not found" in response.json()["detail"]
    
    def test_get_client_projects(self, db_session, auth_headers, sample_user):
        """Test getting client projects list"""
        # Create a client and client project
        test_client = Client(
            name="Test Client 3",
            description="Test client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        client_project = ClientProject(
            name="Test Project for List",
            description="Test project for listing",
            client_id=test_client.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        
        response = client.get("/client-projects/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "client_projects" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["client_projects"]) >= 1
    
    def test_get_client_projects_pagination(self, db_session, auth_headers, sample_user):
        """Test client projects list pagination"""
        # Create a client
        test_client = Client(
            name="Test Client 4",
            description="Test client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        # Create multiple client projects
        for i in range(5):
            client_project = ClientProject(
                name=f"Test Project {i}",
                description=f"Test project {i}",
                client_id=test_client.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(client_project)
        db_session.commit()
        
        # Test pagination
        response = client.get("/client-projects/?page=1&size=2", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["client_projects"]) <= 2
        assert data["page"] == 1
        assert data["size"] == 2
    
    def test_get_client_projects_filter_by_client_id(self, db_session, auth_headers, sample_user):
        """Test filtering client projects by client_id"""
        # Create two clients
        client1 = Client(
            name="Client 1",
            description="First client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        client2 = Client(
            name="Client 2",
            description="Second client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client1)
        db_session.add(client2)
        db_session.commit()
        
        # Create projects for each client
        project1 = ClientProject(
            name="Project 1",
            description="Project for client 1",
            client_id=client1.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        project2 = ClientProject(
            name="Project 2",
            description="Project for client 2",
            client_id=client2.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project1)
        db_session.add(project2)
        db_session.commit()
        
        # Filter by client1
        response = client.get(f"/client-projects/?client_id={client1.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert all(cp["client_id"] == str(client1.id) for cp in data["client_projects"])
    
    def test_get_client_project_by_id(self, db_session, auth_headers, sample_user):
        """Test getting a specific client project by ID"""
        # Create a client and client project
        test_client = Client(
            name="Test Client 5",
            description="Test client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        client_project = ClientProject(
            name="Test Project for Get",
            description="Test project for getting by ID",
            client_id=test_client.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        
        response = client.get(f"/client-projects/{client_project.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(client_project.id)
        assert data["name"] == "Test Project for Get"
    
    def test_get_client_project_not_found(self, db_session, auth_headers):
        """Test getting a non-existent client project returns 404"""
        from uuid import uuid4
        
        response = client.get(f"/client-projects/{uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_client_project(self, db_session, auth_headers, sample_user):
        """Test updating a client project"""
        # Create a client and client project
        test_client = Client(
            name="Test Client 6",
            description="Test client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        client_project = ClientProject(
            name="Test Project for Update",
            description="Test project for updating",
            client_id=test_client.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated project description"
        }
        
        response = client.patch(f"/client-projects/{client_project.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["description"] == "Updated project description"
        assert data["modified_by"] == str(sample_user.id)
    
    def test_update_client_project_partial(self, db_session, auth_headers, sample_user):
        """Test partial update of a client project"""
        # Create a client and client project
        test_client = Client(
            name="Test Client 7",
            description="Test client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        client_project = ClientProject(
            name="Test Project Partial",
            description="Original description",
            client_id=test_client.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        
        # Update only description
        update_data = {
            "description": "Updated description only"
        }
        
        response = client.patch(f"/client-projects/{client_project.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Test Project Partial"  # Unchanged
        assert data["description"] == "Updated description only"  # Updated
    
    def test_delete_client_project(self, db_session, auth_headers, sample_user):
        """Test soft deleting a client project"""
        # Create a client and client project
        test_client = Client(
            name="Test Client 8",
            description="Test client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        client_project = ClientProject(
            name="Test Project for Delete",
            description="Test project for deletion",
            client_id=test_client.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_project)
        db_session.commit()
        
        response = client.delete(f"/client-projects/{client_project.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Client project deleted successfully"
        
        # Verify client project is soft deleted
        db_session.refresh(client_project)
        assert client_project.active == False
        
        # Verify it doesn't appear in list
        response = client.get("/client-projects/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert not any(cp["id"] == str(client_project.id) for cp in data["client_projects"])
    
    def test_create_client_project_permission_required(self, db_session, sample_user):
        """Test that creating a client project requires project:manage permission"""
        # Create a user without project:manage permission
        test_role = Role(
            name="test_role_no_permission",
            description="Test role without project:manage"
        )
        db_session.add(test_role)
        db_session.flush()
        
        # Create a permission that's not project:manage
        test_perm = Permission(
            name="sample:read",
            description="Read samples"
        )
        db_session.add(test_perm)
        db_session.flush()
        
        # Assign permission to role
        role_perm = RolePermission(role_id=test_role.id, permission_id=test_perm.id)
        db_session.add(role_perm)
        
        # Create user with this role
        test_user = User(
            name="Test User No Permission",
            username="testuser_noperm",
            email="test_noperm@example.com",
            password_hash=get_password_hash("testpassword"),
            role_id=test_role.id
        )
        db_session.add(test_user)
        db_session.commit()
        
        # Login as this user
        login_response = client.post(
            "/auth/login",
            json={"username": "testuser_noperm", "password": "testpassword"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a client
        test_client = Client(
            name="Test Client Permission",
            description="Test client",
            created_by=test_user.id,
            modified_by=test_user.id
        )
        db_session.add(test_client)
        db_session.commit()
        
        # Try to create client project without permission
        client_project_data = {
            "name": "Test Project",
            "description": "Test project",
            "client_id": str(test_client.id)
        }
        
        response = client.post("/client-projects/", json=client_project_data, headers=headers)
        assert response.status_code == 403
        assert "project:manage" in response.json()["detail"]

