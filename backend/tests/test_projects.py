"""
Tests for projects API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from models.project import Project, ProjectUser
from models.client import Client, ClientProject
from models.user import User
from models.role import Role
from models.permission import Permission
from models.role_permission import RolePermission
from models.list import ListEntry
from app.core.security import get_password_hash
from datetime import datetime
from uuid import uuid4

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


@pytest.fixture
def test_client(db_session, sample_user):
    """Create a test client"""
    test_client_obj = Client(
        name="Test Client",
        description="Test client for projects",
        created_by=sample_user.id,
        modified_by=sample_user.id
    )
    db_session.add(test_client_obj)
    db_session.commit()
    return test_client_obj


@pytest.fixture
def test_status(db_session):
    """Create a test status list entry"""
    test_status_obj = ListEntry(
        id=uuid4(),
        list_name="project_status",
        entry_name="Active",
        entry_value="active",
        active=True
    )
    db_session.add(test_status_obj)
    db_session.commit()
    return test_status_obj


@pytest.fixture
def test_client_project(db_session, sample_user, test_client):
    """Create a test client project"""
    test_client_project_obj = ClientProject(
        name="Test Client Project",
        description="Test client project",
        client_id=test_client.id,
        created_by=sample_user.id,
        modified_by=sample_user.id
    )
    db_session.add(test_client_project_obj)
    db_session.commit()
    return test_client_project_obj


class TestProjectsAPI:
    """Test projects API endpoints"""
    
    def test_create_project(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test creating a new project"""
        project_data = {
            "name": "Test Project",
            "description": "Test project for API testing",
            "start_date": datetime.now().isoformat(),
            "client_id": str(test_client.id),
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "Test project for API testing"
        assert data["client_id"] == str(test_client.id)
        assert data["status"] == str(test_status.id)
        assert data["active"] == True
        assert data["created_by"] == str(sample_user.id)
    
    def test_create_project_with_client_project(self, db_session, auth_headers, sample_user, test_client, test_status, test_client_project):
        """Test creating a project with client_project_id"""
        project_data = {
            "name": "Test Project with Client Project",
            "description": "Test project linked to client project",
            "start_date": datetime.now().isoformat(),
            "client_id": str(test_client.id),
            "client_project_id": str(test_client_project.id),
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "Test Project with Client Project"
        assert data["client_project_id"] == str(test_client_project.id)
        assert "client_project" in data
        assert data["client_project"]["id"] == str(test_client_project.id)
    
    def test_create_project_auto_name(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test creating a project without name (auto-generated)"""
        project_data = {
            "description": "Test project with auto-generated name",
            "start_date": datetime.now().isoformat(),
            "client_id": str(test_client.id),
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] is not None
        assert len(data["name"]) > 0
        assert test_client.name in data["name"]  # Should include client name
    
    def test_create_project_duplicate_name(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test creating a project with duplicate name fails"""
        # Create first project
        project = Project(
            name="Duplicate Test Project",
            description="First project",
            start_date=datetime.now(),
            client_id=test_client.id,
            status=test_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.commit()
        
        # Try to create another with same name
        project_data = {
            "name": "Duplicate Test Project",
            "description": "Second project",
            "start_date": datetime.now().isoformat(),
            "client_id": str(test_client.id),
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_create_project_invalid_client(self, db_session, auth_headers, test_status):
        """Test creating a project with invalid client_id fails"""
        project_data = {
            "name": "Test Project",
            "description": "Test project",
            "start_date": datetime.now().isoformat(),
            "client_id": str(uuid4()),  # Non-existent client ID
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Client not found" in response.json()["detail"]
    
    def test_create_project_invalid_client_project(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test creating a project with invalid client_project_id fails"""
        project_data = {
            "name": "Test Project",
            "description": "Test project",
            "start_date": datetime.now().isoformat(),
            "client_id": str(test_client.id),
            "client_project_id": str(uuid4()),  # Non-existent client project ID
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Client project not found" in response.json()["detail"]
    
    def test_create_project_client_project_mismatch(self, db_session, auth_headers, sample_user, test_client, test_status, test_client_project):
        """Test creating a project with client_project_id that doesn't belong to client_id fails"""
        # Create another client
        other_client = Client(
            name="Other Client",
            description="Other client",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(other_client)
        db_session.commit()
        
        project_data = {
            "name": "Test Project",
            "description": "Test project",
            "start_date": datetime.now().isoformat(),
            "client_id": str(other_client.id),  # Different client
            "client_project_id": str(test_client_project.id),  # Belongs to test_client
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert response.status_code == 400
        assert "does not belong" in response.json()["detail"]
    
    def test_get_projects(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test getting projects list"""
        # Create a project
        project = Project(
            name="Test Project List",
            description="Test project for list",
            start_date=datetime.now(),
            client_id=test_client.id,
            status=test_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.get("/projects/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["projects"]) > 0
    
    def test_get_projects_with_filters(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test getting projects list with filters"""
        # Create projects
        project1 = Project(
            name="Filtered Project 1",
            description="Test project",
            start_date=datetime.now(),
            client_id=test_client.id,
            status=test_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project1)
        db_session.commit()
        
        # Filter by client_id
        response = client.get(
            f"/projects/?client_id={test_client.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(p["client_id"] == str(test_client.id) for p in data["projects"])
        
        # Filter by status
        response = client.get(
            f"/projects/?status={test_status.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(p["status"] == str(test_status.id) for p in data["projects"])
    
    def test_get_projects_pagination(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test getting projects list with pagination"""
        # Create multiple projects
        for i in range(5):
            project = Project(
                name=f"Pagination Project {i}",
                description="Test project",
                start_date=datetime.now(),
                client_id=test_client.id,
                status=test_status.id,
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(project)
        db_session.commit()
        
        # Get first page
        response = client.get("/projects/?page=1&size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) <= 2
        assert data["page"] == 1
        assert data["size"] == 2
        
        # Get second page
        response = client.get("/projects/?page=2&size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
    
    def test_get_project(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test getting a single project"""
        # Create a project
        project = Project(
            name="Single Test Project",
            description="Test project for single get",
            start_date=datetime.now(),
            client_id=test_client.id,
            status=test_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.get(f"/projects/{project.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(project.id)
        assert data["name"] == "Single Test Project"
        assert "client" in data
        assert data["client"]["id"] == str(test_client.id)
    
    def test_get_project_not_found(self, db_session, auth_headers):
        """Test getting a non-existent project returns 404"""
        response = client.get(f"/projects/{uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_project(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test updating a project"""
        # Create a project
        project = Project(
            name="Update Test Project",
            description="Original description",
            start_date=datetime.now(),
            client_id=test_client.id,
            status=test_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.commit()
        
        # Update project
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description"
        }
        
        response = client.patch(f"/projects/{project.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["description"] == "Updated description"
        assert data["modified_by"] == str(sample_user.id)
    
    def test_update_project_client_project(self, db_session, auth_headers, sample_user, test_client, test_status, test_client_project):
        """Test updating a project's client_project_id"""
        # Create a project
        project = Project(
            name="Update Client Project Test",
            description="Test project",
            start_date=datetime.now(),
            client_id=test_client.id,
            status=test_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.commit()
        
        # Update with client_project_id
        update_data = {
            "client_project_id": str(test_client_project.id)
        }
        
        response = client.patch(f"/projects/{project.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["client_project_id"] == str(test_client_project.id)
        assert "client_project" in data
        assert data["client_project"]["id"] == str(test_client_project.id)
    
    def test_update_project_not_found(self, db_session, auth_headers):
        """Test updating a non-existent project returns 404"""
        update_data = {
            "name": "Updated Name"
        }
        
        response = client.patch(f"/projects/{uuid4()}", json=update_data, headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_delete_project(self, db_session, auth_headers, sample_user, test_client, test_status):
        """Test soft deleting a project"""
        # Create a project
        project = Project(
            name="Delete Test Project",
            description="Test project for deletion",
            start_date=datetime.now(),
            client_id=test_client.id,
            status=test_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.commit()
        
        # Delete project
        response = client.delete(f"/projects/{project.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify project is soft deleted (active=false)
        db_session.refresh(project)
        assert project.active == False
        
        # Verify project is not returned in list
        response = client.get("/projects/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        project_ids = [p["id"] for p in data["projects"]]
        assert str(project.id) not in project_ids
    
    def test_delete_project_not_found(self, db_session, auth_headers):
        """Test deleting a non-existent project returns 404"""
        response = client.delete(f"/projects/{uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_create_project_requires_permission(self, db_session, test_client, test_status):
        """Test that creating a project requires project:manage permission"""
        # Create user without project:manage permission
        test_role = Role(
            name="test_role_no_permission",
            description="Test role without project:manage"
        )
        db_session.add(test_role)
        db_session.flush()
        
        test_user = User(
            name="No Permission User",
            username="nopermuser",
            email="noperm@example.com",
            password_hash=get_password_hash("nopermpassword"),
            role_id=test_role.id
        )
        db_session.add(test_user)
        db_session.commit()
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": "nopermuser", "password": "nopermpassword"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to create project
        project_data = {
            "name": "Test Project",
            "description": "Test project",
            "start_date": datetime.now().isoformat(),
            "client_id": str(test_client.id),
            "status": str(test_status.id)
        }
        
        response = client.post("/projects/", json=project_data, headers=headers)
        assert response.status_code == 403
        assert "project:manage" in response.json()["detail"]
