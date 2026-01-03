"""
Tests for help entries API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.help_entry import HelpEntry
from models.user import User, Role


def test_get_help_entries_as_client_user(client: TestClient, db: Session, client_user_token: str):
    """Test that client users see only their role-filtered help entries"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    response = client.get("/help", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "help_entries" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    
    # Verify all entries are either Client role or public (role_filter is None)
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "Client"]


def test_get_help_entries_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can see all help entries"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = client.get("/help", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["help_entries"]) > 0


def test_get_help_entries_with_role_filter_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can filter help entries by role"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Filter by Client role
    response = client.get("/help?role=Client", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "Client"]


def test_get_help_entries_role_filter_as_non_admin(client: TestClient, db: Session, client_user_token: str):
    """Test that non-admins cannot filter by role"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    response = client.get("/help?role=Administrator", headers=headers)
    assert response.status_code == 403
    assert "Only administrators can filter by role" in response.json()["detail"]


def test_get_help_entries_with_section_filter(client: TestClient, db: Session, client_user_token: str):
    """Test filtering help entries by section"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    response = client.get("/help?section=Viewing Projects", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    for entry in data["help_entries"]:
        assert entry["section"] == "Viewing Projects"


def test_get_contextual_help(client: TestClient, db: Session, client_user_token: str):
    """Test getting contextual help for a specific section"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    response = client.get("/help/contextual?section=Viewing Projects", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["section"] == "Viewing Projects"
    assert "content" in data
    assert data["role_filter"] in [None, "Client"]


def test_get_contextual_help_not_found(client: TestClient, db: Session, client_user_token: str):
    """Test that contextual help returns 404 for non-existent section"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    response = client.get("/help/contextual?section=NonExistentSection", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_help_entry_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test creating a help entry as admin"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    help_data = {
        "section": "Test Section",
        "content": "This is test help content for testing purposes.",
        "role_filter": "Client"
    }
    
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["section"] == "Test Section"
    assert data["content"] == "This is test help content for testing purposes."
    assert data["role_filter"] == "Client"
    assert data["active"] is True


def test_create_help_entry_without_permission(client: TestClient, db: Session, client_user_token: str):
    """Test that non-admins cannot create help entries"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    help_data = {
        "section": "Test Section",
        "content": "This should fail",
        "role_filter": "Client"
    }
    
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 403


def test_update_help_entry_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test updating a help entry as admin"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First create a help entry
    help_data = {
        "section": "Update Test Section",
        "content": "Original content",
        "role_filter": "Client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Update it
    update_data = {
        "content": "Updated content"
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["content"] == "Updated content"
    assert data["section"] == "Update Test Section"  # Should remain unchanged


def test_delete_help_entry_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test soft deleting a help entry as admin"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First create a help entry
    help_data = {
        "section": "Delete Test Section",
        "content": "Content to be deleted",
        "role_filter": "Client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Delete it (soft delete)
    response = client.delete(f"/help/admin/help/{help_id}", headers=headers)
    assert response.status_code == 204
    
    # Verify it's no longer visible (soft deleted)
    get_response = client.get("/help", headers=headers)
    assert get_response.status_code == 200
    help_ids = [entry["id"] for entry in get_response.json()["help_entries"]]
    assert help_id not in help_ids


def test_get_help_entries_pagination(client: TestClient, db: Session, admin_token: str):
    """Test pagination for help entries"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get first page
    response = client.get("/help?page=1&size=2", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["page"] == 1
    assert data["size"] == 2
    assert len(data["help_entries"]) <= 2
    
    # Get second page if there are more entries
    if data["pages"] > 1:
        response2 = client.get("/help?page=2&size=2", headers=headers)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["page"] == 2
        assert len(data2["help_entries"]) <= 2


def test_public_help_entries_visible_to_all(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Test that help entries with role_filter=NULL are visible to all roles"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create a public help entry (role_filter=None)
    help_data = {
        "section": "Public Help Section",
        "content": "This is public help content visible to all roles.",
        "role_filter": None
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Verify admin can see it
    admin_response = client.get("/help", headers=headers_admin)
    admin_help_ids = [entry["id"] for entry in admin_response.json()["help_entries"]]
    assert help_id in admin_help_ids
    
    # Verify client user can see it
    client_response = client.get("/help", headers=headers_client)
    client_help_ids = [entry["id"] for entry in client_response.json()["help_entries"]]
    assert help_id in client_help_ids


# Integration tests for role-based help access
def test_client_user_sees_only_filtered_help(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Integration test: Client user sees only Client-filtered and public help entries"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create help entries for different roles
    client_help = {
        "section": "Client-Specific Help",
        "content": "This is help content for Client users only.",
        "role_filter": "Client"
    }
    lab_help = {
        "section": "Lab Technician Help",
        "content": "This is help content for Lab Technicians only.",
        "role_filter": "Lab Technician"
    }
    public_help = {
        "section": "Public Help",
        "content": "This is public help content.",
        "role_filter": None
    }
    
    # Create all help entries as admin
    client_help_id = client.post("/help/admin/help", json=client_help, headers=headers_admin).json()["id"]
    lab_help_id = client.post("/help/admin/help", json=lab_help, headers=headers_admin).json()["id"]
    public_help_id = client.post("/help/admin/help", json=public_help, headers=headers_admin).json()["id"]
    
    # Client user should see Client and public help, but not Lab Technician help
    response = client.get("/help", headers=headers_client)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert client_help_id in help_ids, "Client user should see Client-specific help"
    assert public_help_id in help_ids, "Client user should see public help"
    assert lab_help_id not in help_ids, "Client user should NOT see Lab Technician help"


def test_non_client_sees_general_help(client: TestClient, db_session: Session, admin_token: str, test_user):
    """Integration test: Non-client users see help entries filtered by their role or public"""
    from app.core.security import create_access_token
    from models.user import Permission, RolePermission, Role
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entries
    client_help = {
        "section": "Client Help",
        "content": "Client-specific content.",
        "role_filter": "Client"
    }
    lab_help = {
        "section": "Lab Technician Help",
        "content": "Lab Technician content.",
        "role_filter": "Lab Technician"
    }
    public_help = {
        "section": "Public Help",
        "content": "Public content.",
        "role_filter": None
    }
    
    client_help_id = client.post("/help/admin/help", json=client_help, headers=headers_admin).json()["id"]
    lab_help_id = client.post("/help/admin/help", json=lab_help, headers=headers_admin).json()["id"]
    public_help_id = client.post("/help/admin/help", json=public_help, headers=headers_admin).json()["id"]
    
    # Create token for test_user (test_role, not Lab Technician)
    role = db_session.query(Role).filter(Role.id == test_user.role_id).first()
    
    permissions = db_session.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == test_user.role_id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(test_user.id),
        "username": test_user.username,
        "role": role.name,
        "permissions": perm_names
    }
    lab_token = create_access_token(token_data)
    headers_lab = {"Authorization": f"Bearer {lab_token}"}
    
    # Non-client user should see public help, but not Client or Lab Technician help
    # (unless their role matches)
    response = client.get("/help", headers=headers_lab)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    # Should see public help
    assert public_help_id in help_ids, "Non-client user should see public help"
    # Should NOT see Client help
    assert client_help_id not in help_ids, "Non-client user should NOT see Client help"


def test_unauthorized_access_denied(client: TestClient):
    """Integration test: Unauthorized requests to help endpoints are denied"""
    # Try to access help without token
    response = client.get("/help")
    assert response.status_code == 403  # FastAPI returns 403 for missing auth
    
    # Try to create help entry without token
    help_data = {
        "section": "Unauthorized Test",
        "content": "This should fail",
        "role_filter": "Client"
    }
    response = client.post("/help/admin/help", json=help_data)
    assert response.status_code == 403
    
    # Try to update help entry without token
    response = client.patch("/help/admin/help/00000000-0000-0000-0000-000000000001", json={"content": "Updated"})
    assert response.status_code == 403
    
    # Try to delete help entry without token
    response = client.delete("/help/admin/help/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 403


def test_client_cannot_access_admin_endpoints(client: TestClient, db: Session, client_user_token: str):
    """Integration test: Client users cannot access admin help CRUD endpoints"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    # Try to create help entry
    help_data = {
        "section": "Unauthorized Create",
        "content": "This should fail",
        "role_filter": "Client"
    }
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 403
    assert "Permission" in response.json()["detail"] or "permission" in response.json()["detail"].lower()
    
    # Try to update help entry
    response = client.patch("/help/admin/help/00000000-0000-0000-0000-000000000001", json={"content": "Updated"}, headers=headers)
    assert response.status_code == 403
    
    # Try to delete help entry
    response = client.delete("/help/admin/help/00000000-0000-0000-0000-000000000001", headers=headers)
    assert response.status_code == 403

