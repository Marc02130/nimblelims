"""
Tests for results API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from models.result import Result
from models.test import Test
from models.sample import Sample
from models.analysis import Analysis, Analyte, AnalysisAnalyte
from models.user import User
from models.role import Role
from models.permission import Permission
from models.role_permission import RolePermission

client = TestClient(app)


class TestResultsAPI:
    """Test results API endpoints"""
    
    def test_create_result(self, db_session, auth_headers, sample_user):
        """Test creating a new result"""
        # Create test data
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client",
            description="Test client for results",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project",
            description="Test project for results",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=None,  # Will be set later
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="Test Sample",
            description="Test sample for results",
            sample_type=None,  # Will be set later
            status=None,  # Will be set later
            matrix=None,  # Will be set later
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis",
            description="Test analysis for results",
            method="Test Method",
            turnaround_time=1,
            cost=100.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analyte
        analyte = Analyte(
            name="Test Analyte",
            description="Test analyte for results",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte)
        db_session.flush()
        
        # Create test
        test = Test(
            name="Test Test",
            description="Test test for results",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=None,  # Will be set later
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test)
        db_session.flush()
        
        result_data = {
            "test_id": str(test.id),
            "analyte_id": str(analyte.id),
            "raw_result": "123.45",
            "reported_result": "123.5",
            "entry_date": "2024-01-01T00:00:00Z",
            "entered_by": str(sample_user.id)
        }
        
        response = client.post("/results/", json=result_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["test_id"] == str(test.id)
        assert data["analyte_id"] == str(analyte.id)
        assert data["raw_result"] == "123.45"
        assert data["reported_result"] == "123.5"
    
    def test_enter_batch_results(self, db_session, auth_headers, sample_user):
        """Test entering results for a batch"""
        # Create test data (similar to previous test)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        from models.batch import Batch
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Batch",
            description="Test client for batch results",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Batch",
            description="Test project for batch results",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="Test Sample for Batch",
            description="Test sample for batch results",
            sample_type=None,
            status=None,
            matrix=None,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis for Batch",
            description="Test analysis for batch results",
            method="Test Method",
            turnaround_time=1,
            cost=100.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analyte
        analyte = Analyte(
            name="Test Analyte for Batch",
            description="Test analyte for batch results",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte)
        db_session.flush()
        
        # Create test
        test = Test(
            name="Test Test for Batch",
            description="Test test for batch results",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test)
        db_session.flush()
        
        # Create batch
        batch = Batch(
            name="Test Batch for Results",
            description="Test batch for results",
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(batch)
        db_session.flush()
        
        batch_results_data = {
            "batch_id": str(batch.id),
            "test_id": str(test.id),
            "results": [
                {
                    "analyte_id": str(analyte.id),
                    "raw_result": "123.45",
                    "reported_result": "123.5"
                }
            ]
        }
        
        response = client.post("/results/batch", json=batch_results_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["test_id"] == str(test.id)
        assert data[0]["analyte_id"] == str(analyte.id)
        assert data[0]["raw_result"] == "123.45"
    
    def test_validate_result(self, db_session, auth_headers, sample_user):
        """Test validating a result"""
        # Create test data
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Validation",
            description="Test client for validation",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Validation",
            description="Test project for validation",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="Test Sample for Validation",
            description="Test sample for validation",
            sample_type=None,
            status=None,
            matrix=None,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis for Validation",
            description="Test analysis for validation",
            method="Test Method",
            turnaround_time=1,
            cost=100.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analyte
        analyte = Analyte(
            name="Test Analyte for Validation",
            description="Test analyte for validation",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte)
        db_session.flush()
        
        # Create test
        test = Test(
            name="Test Test for Validation",
            description="Test test for validation",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test)
        db_session.flush()
        
        # Create analysis_analyte configuration
        analysis_analyte = AnalysisAnalyte(
            analysis_id=analysis.id,
            analyte_id=analyte.id,
            data_type="numeric",
            high_value=1000.0,
            low_value=0.0,
            significant_figures=3,
            is_required=True,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis_analyte)
        db_session.commit()
        
        validation_data = {
            "test_id": str(test.id),
            "analyte_id": str(analyte.id),
            "raw_result": "123.45",
            "reported_result": "123.5"
        }
        
        response = client.post("/results/validate", json=validation_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "significant_figures" in data
        assert "data_type" in data
    
    def test_get_results(self, db_session, auth_headers, sample_user):
        """Test getting results list"""
        # Create test data (similar to previous tests)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for List",
            description="Test client for results list",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for List",
            description="Test project for results list",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="Test Sample for List",
            description="Test sample for results list",
            sample_type=None,
            status=None,
            matrix=None,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis for List",
            description="Test analysis for results list",
            method="Test Method",
            turnaround_time=1,
            cost=100.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analyte
        analyte = Analyte(
            name="Test Analyte for List",
            description="Test analyte for results list",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte)
        db_session.flush()
        
        # Create test
        test = Test(
            name="Test Test for List",
            description="Test test for results list",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test)
        db_session.flush()
        
        # Create result
        result = Result(
            test_id=test.id,
            analyte_id=analyte.id,
            raw_result="123.45",
            reported_result="123.5",
            entered_by=sample_user.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(result)
        db_session.commit()
        
        response = client.get("/results/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["results"]) >= 1
    
    def test_get_result_by_id(self, db_session, auth_headers, sample_user):
        """Test getting a specific result by ID"""
        # Create test data (similar to previous tests)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Get",
            description="Test client for getting result",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Get",
            description="Test project for getting result",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="Test Sample for Get",
            description="Test sample for getting result",
            sample_type=None,
            status=None,
            matrix=None,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis for Get",
            description="Test analysis for getting result",
            method="Test Method",
            turnaround_time=1,
            cost=100.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analyte
        analyte = Analyte(
            name="Test Analyte for Get",
            description="Test analyte for getting result",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte)
        db_session.flush()
        
        # Create test
        test = Test(
            name="Test Test for Get",
            description="Test test for getting result",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test)
        db_session.flush()
        
        # Create result
        result = Result(
            test_id=test.id,
            analyte_id=analyte.id,
            raw_result="123.45",
            reported_result="123.5",
            entered_by=sample_user.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(result)
        db_session.commit()
        
        response = client.get(f"/results/{result.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(result.id)
        assert data["test_id"] == str(test.id)
        assert data["analyte_id"] == str(analyte.id)
        assert data["raw_result"] == "123.45"
        assert data["reported_result"] == "123.5"
    
    def test_update_result(self, db_session, auth_headers, sample_user):
        """Test updating a result"""
        # Create test data (similar to previous tests)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Update",
            description="Test client for updating result",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Update",
            description="Test project for updating result",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="Test Sample for Update",
            description="Test sample for updating result",
            sample_type=None,
            status=None,
            matrix=None,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis for Update",
            description="Test analysis for updating result",
            method="Test Method",
            turnaround_time=1,
            cost=100.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analyte
        analyte = Analyte(
            name="Test Analyte for Update",
            description="Test analyte for updating result",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte)
        db_session.flush()
        
        # Create test
        test = Test(
            name="Test Test for Update",
            description="Test test for updating result",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test)
        db_session.flush()
        
        # Create result
        result = Result(
            test_id=test.id,
            analyte_id=analyte.id,
            raw_result="123.45",
            reported_result="123.5",
            entered_by=sample_user.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(result)
        db_session.commit()
        
        update_data = {
            "raw_result": "456.78",
            "reported_result": "456.8"
        }
        
        response = client.patch(f"/results/{result.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["raw_result"] == "456.78"
        assert data["reported_result"] == "456.8"
    
    def test_delete_result(self, db_session, auth_headers, sample_user):
        """Test deleting a result"""
        # Create test data (similar to previous tests)
        from models.list import ListEntry
        from models.project import Project
        from models.client import Client
        
        # Create client and project
        client_entity = Client(
            name="Test Client for Delete",
            description="Test client for deleting result",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project for Delete",
            description="Test project for deleting result",
            start_date="2024-01-01",
            client_id=client_entity.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create sample
        sample = Sample(
            name="Test Sample for Delete",
            description="Test sample for deleting result",
            sample_type=None,
            status=None,
            matrix=None,
            project_id=project.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample)
        db_session.flush()
        
        # Create analysis
        analysis = Analysis(
            name="Test Analysis for Delete",
            description="Test analysis for deleting result",
            method="Test Method",
            turnaround_time=1,
            cost=100.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        # Create analyte
        analyte = Analyte(
            name="Test Analyte for Delete",
            description="Test analyte for deleting result",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte)
        db_session.flush()
        
        # Create test
        test = Test(
            name="Test Test for Delete",
            description="Test test for deleting result",
            sample_id=sample.id,
            analysis_id=analysis.id,
            status=None,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test)
        db_session.flush()
        
        # Create result
        result = Result(
            test_id=test.id,
            analyte_id=analyte.id,
            raw_result="123.45",
            reported_result="123.5",
            entered_by=sample_user.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(result)
        db_session.commit()
        
        response = client.delete(f"/results/{result.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Result deleted successfully"
        
        # Verify result is soft deleted
        db_session.refresh(result)
        assert result.active == False
