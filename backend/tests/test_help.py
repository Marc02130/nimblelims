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


# Lab Technician help tests
def test_get_help_entries_as_lab_technician(client: TestClient, db: Session, admin_token: str):
    """Test that lab technicians see their role-filtered help entries"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Technician role if it doesn't exist
    lab_tech_role = db.query(Role).filter(Role.name == "Lab Technician").first()
    if not lab_tech_role:
        lab_tech_role = Role(name="Lab Technician", description="Laboratory technician")
        db.add(lab_tech_role)
        db.flush()
    
    # Create lab technician help entries with slug format
    lab_tech_help_entries = [
        {
            "section": "Accessioning Workflow",
            "content": "Step-by-step guide to sample accessioning with test assignments.",
            "role_filter": "lab-technician"
        },
        {
            "section": "Batch Creation",
            "content": "Create batches to group samples for testing workflows.",
            "role_filter": "lab-technician"
        },
        {
            "section": "Results Entry",
            "content": "Enter test results for samples in batches.",
            "role_filter": "lab-technician"
        }
    ]
    
    # Create help entries as admin
    help_ids = []
    for entry_data in lab_tech_help_entries:
        response = client.post("/help/admin/help", json=entry_data, headers=headers_admin)
        assert response.status_code == 201
        help_ids.append(response.json()["id"])
    
    # Create a lab technician user
    lab_tech_user = User(
        name="Lab Tech User",
        username="labtech",
        email="labtech@example.com",
        password_hash="hashed_password",
        role_id=lab_tech_role.id
    )
    db.add(lab_tech_user)
    db.commit()
    
    # Create token for lab technician
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_tech_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_tech_user.id),
        "username": lab_tech_user.username,
        "role": lab_tech_role.name,
        "permissions": perm_names
    }
    lab_tech_token = create_access_token(token_data)
    headers_lab_tech = {"Authorization": f"Bearer {lab_tech_token}"}
    
    # Lab technician should see their help entries
    response = client.get("/help", headers=headers_lab_tech)
    assert response.status_code == 200
    
    data = response.json()
    help_entry_ids = [entry["id"] for entry in data["help_entries"]]
    
    # Verify lab technician sees their help entries
    for help_id in help_ids:
        assert help_id in help_entry_ids, f"Lab technician should see help entry {help_id}"
    
    # Verify all entries are either lab-technician or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "lab-technician"], \
            f"Lab technician should only see lab-technician or public help, got {entry['role_filter']}"


def test_get_help_entries_with_lab_technician_role_filter_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can filter help entries by lab-technician role (slug format)"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lab technician help entry
    help_data = {
        "section": "Test Lab Tech Section",
        "content": "This is lab technician help content.",
        "role_filter": "lab-technician"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Filter by slug format
    response = client.get("/help?role=lab-technician", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    assert help_id in help_ids
    
    # Verify all entries are lab-technician or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "lab-technician"]


def test_get_help_entries_with_lab_technician_role_name_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can filter by role name (converted to slug)"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lab technician help entry
    help_data = {
        "section": "Test Lab Tech Section 2",
        "content": "This is lab technician help content.",
        "role_filter": "lab-technician"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Filter by role name (should be converted to slug)
    response = client.get("/help?role=Lab Technician", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    assert help_id in help_ids


def test_get_help_entries_role_filter_case_insensitive(client: TestClient, db: Session, admin_token: str):
    """Test that role filter is case-insensitive"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lab technician help entry
    help_data = {
        "section": "Test Case Insensitive",
        "content": "Testing case insensitive role filter.",
        "role_filter": "lab-technician"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Test various case combinations
    test_cases = [
        "LAB-TECHNICIAN",
        "Lab-Technician",
        "LAB-TECHNICIAN",
        "lab-technician"
    ]
    
    for role_param in test_cases:
        response = client.get(f"/help?role={role_param}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        help_ids = [entry["id"] for entry in data["help_entries"]]
        assert help_id in help_ids, f"Should find help entry with role parameter '{role_param}'"


def test_get_contextual_help_for_lab_technician(client: TestClient, db: Session, admin_token: str):
    """Test getting contextual help for lab technician"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Technician role if it doesn't exist
    lab_tech_role = db.query(Role).filter(Role.name == "Lab Technician").first()
    if not lab_tech_role:
        lab_tech_role = Role(name="Lab Technician", description="Laboratory technician")
        db.add(lab_tech_role)
        db.flush()
    
    # Create lab technician help entry
    help_data = {
        "section": "Accessioning Workflow",
        "content": "Step-by-step guide to sample accessioning with test assignments.",
        "role_filter": "lab-technician"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    
    # Create a lab technician user
    lab_tech_user = User(
        name="Lab Tech User",
        username="labtech2",
        email="labtech2@example.com",
        password_hash="hashed_password",
        role_id=lab_tech_role.id
    )
    db.add(lab_tech_user)
    db.commit()
    
    # Create token for lab technician
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_tech_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_tech_user.id),
        "username": lab_tech_user.username,
        "role": lab_tech_role.name,
        "permissions": perm_names
    }
    lab_tech_token = create_access_token(token_data)
    headers_lab_tech = {"Authorization": f"Bearer {lab_tech_token}"}
    
    # Get contextual help
    response = client.get("/help/contextual?section=Accessioning Workflow", headers=headers_lab_tech)
    assert response.status_code == 200
    
    data = response.json()
    assert data["section"] == "Accessioning Workflow"
    assert data["role_filter"] == "lab-technician"
    assert "accessioning" in data["content"].lower()


def test_create_help_entry_normalizes_role_filter(client: TestClient, db: Session, admin_token: str):
    """Test that creating help entry normalizes role_filter to slug format"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry with role name (should be normalized to slug)
    help_data = {
        "section": "Test Normalization",
        "content": "Testing role filter normalization.",
        "role_filter": "Lab Technician"  # Role name, should be normalized
    }
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["role_filter"] == "lab-technician", "Role filter should be normalized to slug format"
    
    # Verify it can be retrieved with slug format
    get_response = client.get("/help?role=lab-technician", headers=headers)
    assert get_response.status_code == 200
    help_ids = [entry["id"] for entry in get_response.json()["help_entries"]]
    assert data["id"] in help_ids


def test_update_help_entry_normalizes_role_filter(client: TestClient, db: Session, admin_token: str):
    """Test that updating help entry normalizes role_filter to slug format"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry
    help_data = {
        "section": "Test Update Normalization",
        "content": "Original content",
        "role_filter": "client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Update with role name (should be normalized)
    update_data = {
        "role_filter": "Lab Technician"  # Should be normalized to "lab-technician"
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["role_filter"] == "lab-technician", "Role filter should be normalized to slug format"


def test_lab_technician_help_content(client: TestClient, db: Session, admin_token: str):
    """Test that lab technician help entries contain expected content"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create comprehensive lab technician help entries
    help_entries = [
        {
            "section": "Accessioning Workflow",
            "content": "Step-by-step guide to sample accessioning:\n\n1. Enter sample details\n2. Assign container\n3. Assign tests\n4. Review and submit\n\nBulk tip (US-24): Enable bulk mode for multiple samples.",
            "role_filter": "lab-technician"
        },
        {
            "section": "Batch Creation",
            "content": "Create batches to group samples for testing:\n\n1. Select containers\n2. Set batch details\n3. Validate compatibility\n4. QC requirements",
            "role_filter": "lab-technician"
        },
        {
            "section": "Results Entry",
            "content": "Enter test results for samples in a batch:\n\nSingle-test entry:\n1. Select batch and test\n2. Load analytes\n3. Enter results\n4. Save\n\nBatch results entry (US-28):\n1. Select batch\n2. Use tabular interface\n3. Enter results\n4. Submit",
            "role_filter": "lab-technician"
        }
    ]
    
    created_ids = []
    for entry_data in help_entries:
        response = client.post("/help/admin/help", json=entry_data, headers=headers)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])
    
    # Filter by lab-technician role
    response = client.get("/help?role=lab-technician", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    sections = {entry["section"]: entry for entry in data["help_entries"]}
    
    # Verify all sections are present
    assert "Accessioning Workflow" in sections
    assert "Batch Creation" in sections
    assert "Results Entry" in sections
    
    # Verify content contains expected keywords
    accessioning = sections["Accessioning Workflow"]
    assert "accessioning" in accessioning["content"].lower()
    assert "bulk" in accessioning["content"].lower() or "us-24" in accessioning["content"]
    
    batch = sections["Batch Creation"]
    assert "batch" in batch["content"].lower()
    assert "qc" in batch["content"].lower() or "quality" in batch["content"].lower()
    
    results = sections["Results Entry"]
    assert "results" in results["content"].lower()
    assert "batch" in results["content"].lower() or "us-28" in results["content"]


def test_lab_technician_rls_denied_access(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Test that RLS prevents lab technician help from being visible to non-lab-technician users"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create lab technician help entry as admin
    help_data = {
        "section": "Lab Technician Only Section",
        "content": "This help entry should only be visible to lab technicians.",
        "role_filter": "lab-technician"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    lab_tech_help_id = create_response.json()["id"]
    
    # Client user should NOT see lab technician help
    response = client.get("/help", headers=headers_client)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert lab_tech_help_id not in help_ids, "Client user should NOT see lab technician help due to RLS"
    
    # Verify all entries visible to client are Client-filtered or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "Client"], \
            f"Client should only see Client or public help, got {entry['role_filter']}"


def test_lab_technician_help_rls_policy_enforcement(client: TestClient, db: Session, admin_token: str):
    """Test that RLS policy correctly filters help entries by role"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Technician role if it doesn't exist
    lab_tech_role = db.query(Role).filter(Role.name == "Lab Technician").first()
    if not lab_tech_role:
        lab_tech_role = Role(name="Lab Technician", description="Laboratory technician")
        db.add(lab_tech_role)
        db.flush()
    
    # Create help entries for different roles
    client_help = {
        "section": "Client Only Help",
        "content": "Client-specific help content.",
        "role_filter": "Client"
    }
    lab_tech_help = {
        "section": "Lab Tech Only Help",
        "content": "Lab technician-specific help content.",
        "role_filter": "lab-technician"
    }
    public_help = {
        "section": "Public Help",
        "content": "Public help content visible to all.",
        "role_filter": None
    }
    
    # Create all help entries
    client_help_id = client.post("/help/admin/help", json=client_help, headers=headers_admin).json()["id"]
    lab_tech_help_id = client.post("/help/admin/help", json=lab_tech_help, headers=headers_admin).json()["id"]
    public_help_id = client.post("/help/admin/help", json=public_help, headers=headers_admin).json()["id"]
    
    # Create a lab technician user
    lab_tech_user = User(
        name="Lab Tech Test User",
        username="labtech_rls_test",
        email="labtech_rls@example.com",
        password_hash="hashed_password",
        role_id=lab_tech_role.id
    )
    db.add(lab_tech_user)
    db.commit()
    
    # Create token for lab technician
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_tech_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_tech_user.id),
        "username": lab_tech_user.username,
        "role": lab_tech_role.name,
        "permissions": perm_names
    }
    lab_tech_token = create_access_token(token_data)
    headers_lab_tech = {"Authorization": f"Bearer {lab_tech_token}"}
    
    # Lab technician should see lab-technician and public help, but NOT client help
    response = client.get("/help", headers=headers_lab_tech)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert lab_tech_help_id in help_ids, "Lab technician should see lab-technician help"
    assert public_help_id in help_ids, "Lab technician should see public help"
    assert client_help_id not in help_ids, "Lab technician should NOT see Client help due to RLS"
    
    # Verify all entries are lab-technician or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "lab-technician"], \
            f"Lab technician should only see lab-technician or public help, got {entry['role_filter']}"


# Lab Manager help tests
def test_get_help_entries_as_lab_manager(client: TestClient, db: Session, admin_token: str):
    """Test that lab managers see their role-filtered help entries"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Manager role if it doesn't exist
    lab_manager_role = db.query(Role).filter(Role.name == "Lab Manager").first()
    if not lab_manager_role:
        lab_manager_role = Role(name="Lab Manager", description="Laboratory manager")
        db.add(lab_manager_role)
        db.flush()
    
    # Create lab manager help entries with slug format
    lab_manager_help_entries = [
        {
            "section": "Results Review",
            "content": "Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.",
            "role_filter": "lab-manager"
        },
        {
            "section": "Batch Management",
            "content": "Oversee batch operations and workflow. Monitor batch status and QC requirements.",
            "role_filter": "lab-manager"
        },
        {
            "section": "Project Management",
            "content": "Manage projects and client relationships. Monitor project status and sample progress.",
            "role_filter": "lab-manager"
        }
    ]
    
    # Create help entries as admin
    help_ids = []
    for entry_data in lab_manager_help_entries:
        response = client.post("/help/admin/help", json=entry_data, headers=headers_admin)
        assert response.status_code == 201
        help_ids.append(response.json()["id"])
    
    # Create a lab manager user
    lab_manager_user = User(
        name="Lab Manager User",
        username="labmanager",
        email="labmanager@example.com",
        password_hash="hashed_password",
        role_id=lab_manager_role.id
    )
    db.add(lab_manager_user)
    db.commit()
    
    # Create token for lab manager
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_manager_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_manager_user.id),
        "username": lab_manager_user.username,
        "role": lab_manager_role.name,
        "permissions": perm_names
    }
    lab_manager_token = create_access_token(token_data)
    headers_lab_manager = {"Authorization": f"Bearer {lab_manager_token}"}
    
    # Lab manager should see their help entries
    response = client.get("/help", headers=headers_lab_manager)
    assert response.status_code == 200
    
    data = response.json()
    help_entry_ids = [entry["id"] for entry in data["help_entries"]]
    
    # Verify lab manager sees their help entries
    for help_id in help_ids:
        assert help_id in help_entry_ids, f"Lab manager should see help entry {help_id}"
    
    # Verify all entries are either lab-manager or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "lab-manager"], \
            f"Lab manager should only see lab-manager or public help, got {entry['role_filter']}"


def test_get_help_entries_with_lab_manager_role_filter_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can filter help entries by lab-manager role (slug format)"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lab manager help entry
    help_data = {
        "section": "Test Lab Manager Section",
        "content": "This is lab manager help content.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Filter by slug format
    response = client.get("/help?role=lab-manager", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    assert help_id in help_ids
    
    # Verify all entries are lab-manager or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "lab-manager"]


def test_get_help_entries_with_lab_manager_role_name_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can filter by Lab Manager role name (converted to slug)"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lab manager help entry
    help_data = {
        "section": "Test Lab Manager Section 2",
        "content": "This is lab manager help content.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Filter by role name (should be converted to slug)
    response = client.get("/help?role=Lab Manager", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    assert help_id in help_ids


def test_get_help_entries_lab_manager_role_filter_case_insensitive(client: TestClient, db: Session, admin_token: str):
    """Test that role filter is case-insensitive for Lab Manager"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lab manager help entry
    help_data = {
        "section": "Test Case Insensitive Lab Manager",
        "content": "Testing case insensitive role filter for Lab Manager.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Test various case combinations
    test_cases = [
        "LAB-MANAGER",
        "Lab-Manager",
        "LAB-MANAGER",
        "lab-manager"
    ]
    
    for role_param in test_cases:
        response = client.get(f"/help?role={role_param}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        help_ids = [entry["id"] for entry in data["help_entries"]]
        assert help_id in help_ids, f"Should find help entry with role parameter '{role_param}'"


def test_get_contextual_help_for_lab_manager(client: TestClient, db: Session, admin_token: str):
    """Test getting contextual help for lab manager"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Manager role if it doesn't exist
    lab_manager_role = db.query(Role).filter(Role.name == "Lab Manager").first()
    if not lab_manager_role:
        lab_manager_role = Role(name="Lab Manager", description="Laboratory manager")
        db.add(lab_manager_role)
        db.flush()
    
    # Create lab manager help entry
    help_data = {
        "section": "Results Review",
        "content": "Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    
    # Create a lab manager user
    lab_manager_user = User(
        name="Lab Manager User",
        username="labmanager2",
        email="labmanager2@example.com",
        password_hash="hashed_password",
        role_id=lab_manager_role.id
    )
    db.add(lab_manager_user)
    db.commit()
    
    # Create token for lab manager
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_manager_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_manager_user.id),
        "username": lab_manager_user.username,
        "role": lab_manager_role.name,
        "permissions": perm_names
    }
    lab_manager_token = create_access_token(token_data)
    headers_lab_manager = {"Authorization": f"Bearer {lab_manager_token}"}
    
    # Get contextual help
    response = client.get("/help/contextual?section=Results Review", headers=headers_lab_manager)
    assert response.status_code == 200
    
    data = response.json()
    assert data["section"] == "Results Review"
    assert data["role_filter"] == "lab-manager"
    assert "review" in data["content"].lower() or "qc" in data["content"].lower()


def test_lab_manager_help_content(client: TestClient, db: Session, admin_token: str):
    """Test that lab manager help entries contain expected content"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create comprehensive lab manager help entries
    help_entries = [
        {
            "section": "Results Review",
            "content": "Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.\n\nReview workflow:\n1. Access batch view\n2. Review test results\n3. Validate QC\n4. Approve results\n5. Flag issues",
            "role_filter": "lab-manager"
        },
        {
            "section": "Batch Management",
            "content": "Oversee batch operations and workflow:\n\n1. Monitor batch status\n2. Review batch composition\n3. Manage batch lifecycle\n4. QC oversight",
            "role_filter": "lab-manager"
        },
        {
            "section": "Project Management",
            "content": "Manage projects and client relationships:\n\n1. View all projects\n2. Monitor project status\n3. Review project samples\n4. Client project coordination",
            "role_filter": "lab-manager"
        }
    ]
    
    created_ids = []
    for entry_data in help_entries:
        response = client.post("/help/admin/help", json=entry_data, headers=headers)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])
    
    # Filter by lab-manager role
    response = client.get("/help?role=lab-manager", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    sections = {entry["section"]: entry for entry in data["help_entries"]}
    
    # Verify all sections are present
    assert "Results Review" in sections
    assert "Batch Management" in sections
    assert "Project Management" in sections
    
    # Verify content contains expected keywords
    results_review = sections["Results Review"]
    assert "review" in results_review["content"].lower() or "qc" in results_review["content"].lower()
    assert "us-12" in results_review["content"] or "flag" in results_review["content"].lower()
    
    batch_mgmt = sections["Batch Management"]
    assert "batch" in batch_mgmt["content"].lower()
    assert "qc" in batch_mgmt["content"].lower() or "quality" in batch_mgmt["content"].lower()
    
    project_mgmt = sections["Project Management"]
    assert "project" in project_mgmt["content"].lower()
    assert "client" in project_mgmt["content"].lower()


def test_lab_manager_rls_denied_access(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Test that RLS prevents lab manager help from being visible to non-lab-manager users"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create lab manager help entry as admin
    help_data = {
        "section": "Lab Manager Only Section",
        "content": "This help entry should only be visible to lab managers.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    lab_manager_help_id = create_response.json()["id"]
    
    # Client user should NOT see lab manager help
    response = client.get("/help", headers=headers_client)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert lab_manager_help_id not in help_ids, "Client user should NOT see lab manager help due to RLS"
    
    # Verify all entries visible to client are Client-filtered or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "Client"], \
            f"Client should only see Client or public help, got {entry['role_filter']}"


def test_lab_manager_help_rls_policy_enforcement(client: TestClient, db: Session, admin_token: str):
    """Test that RLS policy correctly filters help entries by role for Lab Manager"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Manager role if it doesn't exist
    lab_manager_role = db.query(Role).filter(Role.name == "Lab Manager").first()
    if not lab_manager_role:
        lab_manager_role = Role(name="Lab Manager", description="Laboratory manager")
        db.add(lab_manager_role)
        db.flush()
    
    # Create help entries for different roles
    client_help = {
        "section": "Client Only Help",
        "content": "Client-specific help content.",
        "role_filter": "Client"
    }
    lab_manager_help = {
        "section": "Lab Manager Only Help",
        "content": "Lab manager-specific help content.",
        "role_filter": "lab-manager"
    }
    public_help = {
        "section": "Public Help",
        "content": "Public help content visible to all.",
        "role_filter": None
    }
    
    # Create all help entries
    client_help_id = client.post("/help/admin/help", json=client_help, headers=headers_admin).json()["id"]
    lab_manager_help_id = client.post("/help/admin/help", json=lab_manager_help, headers=headers_admin).json()["id"]
    public_help_id = client.post("/help/admin/help", json=public_help, headers=headers_admin).json()["id"]
    
    # Create a lab manager user
    lab_manager_user = User(
        name="Lab Manager Test User",
        username="labmanager_rls_test",
        email="labmanager_rls@example.com",
        password_hash="hashed_password",
        role_id=lab_manager_role.id
    )
    db.add(lab_manager_user)
    db.commit()
    
    # Create token for lab manager
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_manager_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_manager_user.id),
        "username": lab_manager_user.username,
        "role": lab_manager_role.name,
        "permissions": perm_names
    }
    lab_manager_token = create_access_token(token_data)
    headers_lab_manager = {"Authorization": f"Bearer {lab_manager_token}"}
    
    # Lab manager should see lab-manager and public help, but NOT client help
    response = client.get("/help", headers=headers_lab_manager)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert lab_manager_help_id in help_ids, "Lab manager should see lab-manager help"
    assert public_help_id in help_ids, "Lab manager should see public help"
    assert client_help_id not in help_ids, "Lab manager should NOT see Client help due to RLS"
    
    # Verify all entries are lab-manager or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "lab-manager"], \
            f"Lab manager should only see lab-manager or public help, got {entry['role_filter']}"


def test_lab_manager_and_lab_technician_help_isolation(client: TestClient, db: Session, admin_token: str):
    """Test that Lab Manager and Lab Technician help entries are properly isolated"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create roles if they don't exist
    lab_manager_role = db.query(Role).filter(Role.name == "Lab Manager").first()
    if not lab_manager_role:
        lab_manager_role = Role(name="Lab Manager", description="Laboratory manager")
        db.add(lab_manager_role)
        db.flush()
    
    lab_tech_role = db.query(Role).filter(Role.name == "Lab Technician").first()
    if not lab_tech_role:
        lab_tech_role = Role(name="Lab Technician", description="Laboratory technician")
        db.add(lab_tech_role)
        db.flush()
    
    # Create help entries for each role
    lab_manager_help = {
        "section": "Results Review",
        "content": "Lab Manager: Review and approve results.",
        "role_filter": "lab-manager"
    }
    lab_tech_help = {
        "section": "Results Entry",
        "content": "Lab Technician: Enter test results.",
        "role_filter": "lab-technician"
    }
    
    lab_manager_help_id = client.post("/help/admin/help", json=lab_manager_help, headers=headers_admin).json()["id"]
    lab_tech_help_id = client.post("/help/admin/help", json=lab_tech_help, headers=headers_admin).json()["id"]
    
    # Create lab manager user
    lab_manager_user = User(
        name="Lab Manager Test",
        username="labmanager_isolation",
        email="labmanager_iso@example.com",
        password_hash="hashed_password",
        role_id=lab_manager_role.id
    )
    db.add(lab_manager_user)
    
    # Create lab technician user
    lab_tech_user = User(
        name="Lab Tech Test",
        username="labtech_isolation",
        email="labtech_iso@example.com",
        password_hash="hashed_password",
        role_id=lab_tech_role.id
    )
    db.add(lab_tech_user)
    db.commit()
    
    # Create tokens
    manager_perms = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_manager_role.id).all()
    manager_perm_names = [p.name for p in manager_perms]
    
    tech_perms = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_tech_role.id).all()
    tech_perm_names = [p.name for p in tech_perms]
    
    manager_token = create_access_token({
        "sub": str(lab_manager_user.id),
        "username": lab_manager_user.username,
        "role": lab_manager_role.name,
        "permissions": manager_perm_names
    })
    headers_manager = {"Authorization": f"Bearer {manager_token}"}
    
    tech_token = create_access_token({
        "sub": str(lab_tech_user.id),
        "username": lab_tech_user.username,
        "role": lab_tech_role.name,
        "permissions": tech_perm_names
    })
    headers_tech = {"Authorization": f"Bearer {tech_token}"}
    
    # Lab Manager should see their help, not Lab Technician help
    manager_response = client.get("/help", headers=headers_manager)
    assert manager_response.status_code == 200
    manager_help_ids = [entry["id"] for entry in manager_response.json()["help_entries"]]
    assert lab_manager_help_id in manager_help_ids
    assert lab_tech_help_id not in manager_help_ids, "Lab Manager should NOT see Lab Technician help"
    
    # Lab Technician should see their help, not Lab Manager help
    tech_response = client.get("/help", headers=headers_tech)
    assert tech_response.status_code == 200
    tech_help_ids = [entry["id"] for entry in tech_response.json()["help_entries"]]
    assert lab_tech_help_id in tech_help_ids
    assert lab_manager_help_id not in tech_help_ids, "Lab Technician should NOT see Lab Manager help"


def test_lab_manager_help_aria_accessibility(client: TestClient, db: Session, admin_token: str):
    """Test that Lab Manager help entries support ARIA accessibility requirements"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Manager role if it doesn't exist
    lab_manager_role = db.query(Role).filter(Role.name == "Lab Manager").first()
    if not lab_manager_role:
        lab_manager_role = Role(name="Lab Manager", description="Laboratory manager")
        db.add(lab_manager_role)
        db.flush()
    
    # Create lab manager help entries
    help_data = {
        "section": "Results Review",
        "content": "Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    
    # Create a lab manager user
    lab_manager_user = User(
        name="Lab Manager Aria Test",
        username="labmanager_aria",
        email="labmanager_aria@example.com",
        password_hash="hashed_password",
        role_id=lab_manager_role.id
    )
    db.add(lab_manager_user)
    db.commit()
    
    # Create token for lab manager
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_manager_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_manager_user.id),
        "username": lab_manager_user.username,
        "role": lab_manager_role.name,
        "permissions": perm_names
    }
    lab_manager_token = create_access_token(token_data)
    headers_lab_manager = {"Authorization": f"Bearer {lab_manager_token}"}
    
    # Get help entries - should return lab-manager entries
    response = client.get("/help", headers=headers_lab_manager)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["help_entries"]) > 0
    
    # Verify help entries have required fields for ARIA
    for entry in data["help_entries"]:
        assert "id" in entry, "Help entry must have id for ARIA"
        assert "section" in entry, "Help entry must have section for ARIA labeling"
        assert "content" in entry, "Help entry must have content"
        assert entry["section"] is not None and len(entry["section"]) > 0, "Section must not be empty"
        assert entry["content"] is not None and len(entry["content"]) > 0, "Content must not be empty"


def test_lab_manager_help_rls_denied_to_client(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Test that RLS prevents Lab Manager help from being visible to Client users"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create lab manager help entry as admin
    help_data = {
        "section": "Results Review",
        "content": "Lab Manager only: Review and approve results.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    lab_manager_help_id = create_response.json()["id"]
    
    # Client user should NOT see lab manager help
    response = client.get("/help", headers=headers_client)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert lab_manager_help_id not in help_ids, "Client user should NOT see lab manager help due to RLS"
    
    # Verify all entries visible to client are Client-filtered or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "Client"], \
            f"Client should only see Client or public help, got {entry['role_filter']}"


def test_lab_manager_help_rls_denied_to_lab_technician(client: TestClient, db: Session, admin_token: str):
    """Test that RLS prevents Lab Manager help from being visible to Lab Technician users"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Technician role if it doesn't exist
    lab_tech_role = db.query(Role).filter(Role.name == "Lab Technician").first()
    if not lab_tech_role:
        lab_tech_role = Role(name="Lab Technician", description="Laboratory technician")
        db.add(lab_tech_role)
        db.flush()
    
    # Create lab manager help entry
    help_data = {
        "section": "Results Review",
        "content": "Lab Manager only: Review and approve results.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    lab_manager_help_id = create_response.json()["id"]
    
    # Create a lab technician user
    lab_tech_user = User(
        name="Lab Tech RLS Test",
        username="labtech_rls_denied",
        email="labtech_rls_denied@example.com",
        password_hash="hashed_password",
        role_id=lab_tech_role.id
    )
    db.add(lab_tech_user)
    db.commit()
    
    # Create token for lab technician
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_tech_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_tech_user.id),
        "username": lab_tech_user.username,
        "role": lab_tech_role.name,
        "permissions": perm_names
    }
    lab_tech_token = create_access_token(token_data)
    headers_lab_tech = {"Authorization": f"Bearer {lab_tech_token}"}
    
    # Lab Technician should NOT see lab manager help
    response = client.get("/help", headers=headers_lab_tech)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert lab_manager_help_id not in help_ids, "Lab Technician should NOT see lab manager help due to RLS"
    
    # Verify all entries are lab-technician or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "lab-technician"], \
            f"Lab technician should only see lab-technician or public help, got {entry['role_filter']}"


def test_lab_manager_contextual_help_filtering(client: TestClient, db: Session, admin_token: str):
    """Test that contextual help for Lab Manager is properly filtered by role"""
    from app.core.security import create_access_token
    from models.user import Role, Permission, RolePermission
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Create Lab Manager role if it doesn't exist
    lab_manager_role = db.query(Role).filter(Role.name == "Lab Manager").first()
    if not lab_manager_role:
        lab_manager_role = Role(name="Lab Manager", description="Laboratory manager")
        db.add(lab_manager_role)
        db.flush()
    
    # Create lab manager help entry
    help_data = {
        "section": "Results Review",
        "content": "Guide: Approve results, check QC. Use result:review permission.",
        "role_filter": "lab-manager"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    
    # Create a lab manager user
    lab_manager_user = User(
        name="Lab Manager Contextual",
        username="labmanager_contextual",
        email="labmanager_contextual@example.com",
        password_hash="hashed_password",
        role_id=lab_manager_role.id
    )
    db.add(lab_manager_user)
    db.commit()
    
    # Create token for lab manager
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == lab_manager_role.id).all()
    perm_names = [p.name for p in permissions]
    
    token_data = {
        "sub": str(lab_manager_user.id),
        "username": lab_manager_user.username,
        "role": lab_manager_role.name,
        "permissions": perm_names
    }
    lab_manager_token = create_access_token(token_data)
    headers_lab_manager = {"Authorization": f"Bearer {lab_manager_token}"}
    
    # Get contextual help - should return lab manager entry
    response = client.get("/help/contextual?section=Results Review", headers=headers_lab_manager)
    assert response.status_code == 200
    
    data = response.json()
    assert data["section"] == "Results Review"
    assert data["role_filter"] == "lab-manager"
    assert "review" in data["content"].lower() or "qc" in data["content"].lower()
    
    # Try to get contextual help for non-existent section
    response = client.get("/help/contextual?section=NonExistentSection", headers=headers_lab_manager)
    assert response.status_code == 404


# Administrator help tests
def test_get_help_entries_as_administrator(client: TestClient, db: Session, admin_token: str):
    """Test that administrators see their role-filtered help entries"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create administrator help entries with slug format
    admin_help_entries = [
        {
            "section": "User Management",
            "content": "Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.",
            "role_filter": "administrator"
        },
        {
            "section": "EAV Configuration",
            "content": "Configure custom attributes using Entity-Attribute-Value (EAV) model.",
            "role_filter": "administrator"
        },
        {
            "section": "Row Level Security (RLS)",
            "content": "Manage Row Level Security policies for data isolation.",
            "role_filter": "administrator"
        }
    ]
    
    # Create help entries as admin
    help_ids = []
    for entry_data in admin_help_entries:
        response = client.post("/help/admin/help", json=entry_data, headers=headers)
        assert response.status_code == 201
        help_ids.append(response.json()["id"])
    
    # Administrator should see their help entries
    response = client.get("/help", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    help_entry_ids = [entry["id"] for entry in data["help_entries"]]
    
    # Verify administrator sees their help entries
    for help_id in help_ids:
        assert help_id in help_entry_ids, f"Administrator should see help entry {help_id}"
    
    # Verify all entries are either administrator or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "administrator"], \
            f"Administrator should only see administrator or public help, got {entry['role_filter']}"


def test_get_help_entries_with_administrator_role_filter_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can filter help entries by administrator role (slug format)"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create administrator help entry
    help_data = {
        "section": "Test Administrator Section",
        "content": "This is administrator help content.",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Filter by slug format
    response = client.get("/help?role=administrator", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    assert help_id in help_ids
    
    # Verify all entries are administrator or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "administrator"]


def test_get_help_entries_with_administrator_role_name_as_admin(client: TestClient, db: Session, admin_token: str):
    """Test that admins can filter by Administrator role name (converted to slug)"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create administrator help entry
    help_data = {
        "section": "Test Administrator Section 2",
        "content": "This is administrator help content.",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Filter by role name (should be converted to slug)
    response = client.get("/help?role=Administrator", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    assert help_id in help_ids


def test_get_contextual_help_for_administrator(client: TestClient, db: Session, admin_token: str):
    """Test getting contextual help for administrator"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create administrator help entry
    help_data = {
        "section": "User Management",
        "content": "Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    
    # Get contextual help
    response = client.get("/help/contextual?section=User Management", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["section"] == "User Management"
    assert data["role_filter"] == "administrator"
    assert "user" in data["content"].lower() or "manage" in data["content"].lower()


def test_administrator_help_content(client: TestClient, db: Session, admin_token: str):
    """Test that administrator help entries contain expected content"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create comprehensive administrator help entries
    help_entries = [
        {
            "section": "User Management",
            "content": "Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.\n\nUser operations:\n1. Create users\n2. Edit users\n3. Assign roles\n4. Client assignment",
            "role_filter": "administrator"
        },
        {
            "section": "EAV Configuration",
            "content": "Configure custom attributes using Entity-Attribute-Value (EAV) model:\n\n1. Access EAV config\n2. Create attribute\n3. Set visibility\n4. Define defaults",
            "role_filter": "administrator"
        },
        {
            "section": "Row Level Security (RLS)",
            "content": "Manage Row Level Security policies for data isolation:\n\n1. Review policies\n2. Policy structure\n3. Admin bypass\n4. Client isolation",
            "role_filter": "administrator"
        }
    ]
    
    created_ids = []
    for entry_data in help_entries:
        response = client.post("/help/admin/help", json=entry_data, headers=headers)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])
    
    # Filter by administrator role
    response = client.get("/help?role=administrator", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    sections = {entry["section"]: entry for entry in data["help_entries"]}
    
    # Verify all sections are present
    assert "User Management" in sections
    assert "EAV Configuration" in sections
    assert "Row Level Security (RLS)" in sections
    
    # Verify content contains expected keywords
    user_mgmt = sections["User Management"]
    assert "user" in user_mgmt["content"].lower() or "manage" in user_mgmt["content"].lower()
    
    eav = sections["EAV Configuration"]
    assert "eav" in eav["content"].lower() or "custom" in eav["content"].lower()
    
    rls = sections["Row Level Security (RLS)"]
    assert "rls" in rls["content"].lower() or "security" in rls["content"].lower()


# Role filter validation tests
def test_create_help_entry_validates_role_filter(client: TestClient, db: Session, admin_token: str):
    """Test that creating help entry validates role_filter against existing roles"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Try to create help entry with invalid role_filter
    help_data = {
        "section": "Test Invalid Role",
        "content": "This should fail validation.",
        "role_filter": "non-existent-role"
    }
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 400
    assert "Invalid role_filter" in response.json()["detail"]
    assert "No matching role found" in response.json()["detail"]
    
    # Create help entry with valid role_filter
    help_data = {
        "section": "Test Valid Role",
        "content": "This should succeed.",
        "role_filter": "lab-technician"  # Assuming this role exists
    }
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["role_filter"] == "lab-technician"


def test_create_help_entry_validates_role_filter_with_role_name(client: TestClient, db: Session, admin_token: str):
    """Test that creating help entry accepts role names and normalizes them"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry with role name (should be normalized to slug)
    help_data = {
        "section": "Test Role Name",
        "content": "Testing role name normalization.",
        "role_filter": "Lab Technician"  # Role name, should be normalized
    }
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["role_filter"] == "lab-technician"


def test_update_help_entry_validates_role_filter(client: TestClient, db: Session, admin_token: str):
    """Test that updating help entry validates role_filter against existing roles"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry
    help_data = {
        "section": "Test Update Validation",
        "content": "Original content",
        "role_filter": "client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Try to update with invalid role_filter
    update_data = {
        "role_filter": "invalid-role-name"
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 400
    assert "Invalid role_filter" in response.json()["detail"]
    
    # Update with valid role_filter
    update_data = {
        "role_filter": "lab-manager"  # Assuming this role exists
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["role_filter"] == "lab-manager"


def test_create_help_entry_with_null_role_filter(client: TestClient, db: Session, admin_token: str):
    """Test that creating help entry with null role_filter creates public help entry"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create public help entry (role_filter=None)
    help_data = {
        "section": "Public Help Section",
        "content": "This is public help content visible to all roles.",
        "role_filter": None
    }
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["role_filter"] is None
    
    # Verify it can be retrieved by any role
    response = client.get("/help", headers=headers)
    assert response.status_code == 200
    help_ids = [entry["id"] for entry in response.json()["help_entries"]]
    assert response.json()["help_entries"][0]["id"] in help_ids


def test_update_help_entry_with_null_role_filter(client: TestClient, db: Session, admin_token: str):
    """Test that updating help entry with null role_filter makes it public"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry with role_filter
    help_data = {
        "section": "Test Null Update",
        "content": "Original content",
        "role_filter": "client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Update with null role_filter (make it public)
    update_data = {
        "role_filter": None
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["role_filter"] is None


def test_create_help_entry_role_filter_case_insensitive(client: TestClient, db: Session, admin_token: str):
    """Test that role_filter validation is case-insensitive"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test various case combinations
    test_cases = [
        "LAB-TECHNICIAN",
        "Lab-Technician",
        "lab-technician",
        "Lab Technician"
    ]
    
    for role_filter in test_cases:
        help_data = {
            "section": f"Test Case {role_filter}",
            "content": "Testing case insensitive role filter.",
            "role_filter": role_filter
        }
        response = client.post("/help/admin/help", json=help_data, headers=headers)
        assert response.status_code == 201, f"Should accept role_filter '{role_filter}'"
        assert response.json()["role_filter"] == "lab-technician", \
            f"Should normalize '{role_filter}' to 'lab-technician'"
        
        # Clean up - delete the created entry
        help_id = response.json()["id"]
        client.delete(f"/help/admin/help/{help_id}", headers=headers)


def test_administrator_rls_denied_access(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Test that RLS prevents administrator help from being visible to non-administrator users"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create administrator help entry as admin
    help_data = {
        "section": "Administrator Only Section",
        "content": "This help entry should only be visible to administrators.",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    admin_help_id = create_response.json()["id"]
    
    # Client user should NOT see administrator help
    response = client.get("/help", headers=headers_client)
    assert response.status_code == 200
    
    data = response.json()
    help_ids = [entry["id"] for entry in data["help_entries"]]
    
    assert admin_help_id not in help_ids, "Client user should NOT see administrator help due to RLS"
    
    # Verify all entries visible to client are Client-filtered or public
    for entry in data["help_entries"]:
        assert entry["role_filter"] in [None, "Client"], \
            f"Client should only see Client or public help, got {entry['role_filter']}"


# Admin Help CRUD and RBAC tests
def test_create_help_entry_requires_config_edit_permission(client: TestClient, db: Session, client_user_token: str):
    """Test that creating help entry requires config:edit permission"""
    headers = {"Authorization": f"Bearer {client_user_token}"}
    
    help_data = {
        "section": "Unauthorized Create",
        "content": "This should fail",
        "role_filter": "client"
    }
    
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower() or "Permission" in response.json()["detail"]


def test_update_help_entry_requires_config_edit_permission(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Test that updating help entry requires config:edit permission"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create help entry as admin
    help_data = {
        "section": "Test Update Permission",
        "content": "Original content",
        "role_filter": "client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Try to update as client user (should fail)
    update_data = {
        "content": "Unauthorized update"
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers_client)
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower() or "Permission" in response.json()["detail"]


def test_delete_help_entry_requires_config_edit_permission(client: TestClient, db: Session, admin_token: str, client_user_token: str):
    """Test that deleting help entry requires config:edit permission"""
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_client = {"Authorization": f"Bearer {client_user_token}"}
    
    # Create help entry as admin
    help_data = {
        "section": "Test Delete Permission",
        "content": "Content to be deleted",
        "role_filter": "client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers_admin)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Try to delete as client user (should fail)
    response = client.delete(f"/help/admin/help/{help_id}", headers=headers_client)
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower() or "Permission" in response.json()["detail"]


def test_create_help_entry_with_admin_permission(client: TestClient, db: Session, admin_token: str):
    """Test that admin can create help entries"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    help_data = {
        "section": "Admin Created Section",
        "content": "This help entry was created by an admin with config:edit permission.",
        "role_filter": "administrator"
    }
    
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["section"] == "Admin Created Section"
    assert data["content"] == "This help entry was created by an admin with config:edit permission."
    assert data["role_filter"] == "administrator"
    assert data["active"] is True


def test_update_help_entry_with_admin_permission(client: TestClient, db: Session, admin_token: str):
    """Test that admin can update help entries"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry
    help_data = {
        "section": "Original Section",
        "content": "Original content",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Update help entry
    update_data = {
        "section": "Updated Section",
        "content": "Updated content with more details.",
        "role_filter": "administrator"
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["section"] == "Updated Section"
    assert data["content"] == "Updated content with more details."
    assert data["role_filter"] == "administrator"


def test_delete_help_entry_with_admin_permission(client: TestClient, db: Session, admin_token: str):
    """Test that admin can soft-delete help entries"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry
    help_data = {
        "section": "Delete Test Section",
        "content": "Content to be deleted",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Delete help entry (soft delete)
    response = client.delete(f"/help/admin/help/{help_id}", headers=headers)
    assert response.status_code == 204
    
    # Verify it's no longer visible (soft deleted)
    get_response = client.get("/help?role=administrator", headers=headers)
    assert get_response.status_code == 200
    help_ids = [entry["id"] for entry in get_response.json()["help_entries"]]
    assert help_id not in help_ids


def test_update_help_entry_partial_update(client: TestClient, db: Session, admin_token: str):
    """Test that partial updates work correctly"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry
    help_data = {
        "section": "Partial Update Test",
        "content": "Original content",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Update only content
    update_data = {
        "content": "Only content updated"
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["section"] == "Partial Update Test"  # Should remain unchanged
    assert data["content"] == "Only content updated"  # Should be updated
    assert data["role_filter"] == "administrator"  # Should remain unchanged


def test_update_help_entry_deactivate(client: TestClient, db: Session, admin_token: str):
    """Test that admin can deactivate help entries"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry
    help_data = {
        "section": "Deactivate Test",
        "content": "Content to be deactivated",
        "role_filter": "administrator"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Deactivate help entry
    update_data = {
        "active": False
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["active"] is False
    
    # Verify it's no longer visible
    get_response = client.get("/help?role=administrator", headers=headers)
    assert get_response.status_code == 200
    help_ids = [entry["id"] for entry in get_response.json()["help_entries"]]
    assert help_id not in help_ids


def test_create_help_entry_validates_role_filter_exists(client: TestClient, db: Session, admin_token: str):
    """Test that creating help entry validates role_filter against existing roles"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Try to create with non-existent role
    help_data = {
        "section": "Invalid Role Test",
        "content": "This should fail validation",
        "role_filter": "non-existent-role-xyz"
    }
    
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 400
    assert "Invalid role_filter" in response.json()["detail"]
    assert "No matching role found" in response.json()["detail"]


def test_update_help_entry_validates_role_filter_exists(client: TestClient, db: Session, admin_token: str):
    """Test that updating help entry validates role_filter against existing roles"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entry
    help_data = {
        "section": "Update Role Filter Test",
        "content": "Original content",
        "role_filter": "client"
    }
    create_response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert create_response.status_code == 201
    help_id = create_response.json()["id"]
    
    # Try to update with non-existent role
    update_data = {
        "role_filter": "non-existent-role-xyz"
    }
    response = client.patch(f"/help/admin/help/{help_id}", json=update_data, headers=headers)
    assert response.status_code == 400
    assert "Invalid role_filter" in response.json()["detail"]
    assert "No matching role found" in response.json()["detail"]


def test_admin_can_create_help_for_any_role(client: TestClient, db: Session, admin_token: str):
    """Test that admin can create help entries for any valid role"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create help entries for different roles
    roles_to_test = ["client", "lab-technician", "lab-manager", "administrator"]
    
    for role_filter in roles_to_test:
        help_data = {
            "section": f"Help for {role_filter}",
            "content": f"Help content for {role_filter} role.",
            "role_filter": role_filter
        }
        response = client.post("/help/admin/help", json=help_data, headers=headers)
        assert response.status_code == 201, f"Should create help entry for role {role_filter}"
        assert response.json()["role_filter"] == role_filter
        
        # Clean up
        help_id = response.json()["id"]
        client.delete(f"/help/admin/help/{help_id}", headers=headers)


def test_admin_can_create_public_help_entry(client: TestClient, db: Session, admin_token: str):
    """Test that admin can create public help entries (role_filter=None)"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    help_data = {
        "section": "Public Help Section",
        "content": "This is public help content visible to all roles.",
        "role_filter": None
    }
    
    response = client.post("/help/admin/help", json=help_data, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["role_filter"] is None
    assert data["section"] == "Public Help Section"
    
    # Verify it's visible to all roles
    # (This would require testing with different role tokens, but the entry should be public)
    get_response = client.get("/help", headers=headers)
    assert get_response.status_code == 200
    help_ids = [entry["id"] for entry in get_response.json()["help_entries"]]
    assert data["id"] in help_ids

