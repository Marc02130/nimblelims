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

    def test_enter_batch_results_us28_success(self, db_session, auth_headers, sample_user):
        """Test batch results entry (US-28) - successful entry"""
        from models.batch import Batch, BatchContainer
        from models.container import Container, Contents, ContainerType
        from models.sample import Sample
        from models.test import Test
        from models.analysis import Analysis, Analyte, AnalysisAnalyte
        from models.project import Project
        from models.client import Client
        from models.list import List, ListEntry
        from datetime import datetime
        from uuid import uuid4
        
        # Create client and project
        client_entity = Client(
            name="Test Client",
            description="Test client",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project",
            description="Test project",
            start_date=datetime.utcnow(),
            client_id=client_entity.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Create list entries
        batch_status_list = db_session.query(List).filter(List.name == "batch_status").first()
        if not batch_status_list:
            batch_status_list = List(
                name="batch_status",
                description="Batch status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(batch_status_list)
            db_session.flush()
        
        batch_status = ListEntry(
            list_id=batch_status_list.id,
            name="Created",
            description="Batch created",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(batch_status)
        db_session.flush()
        
        test_status_list = db_session.query(List).filter(List.name == "test_status").first()
        if not test_status_list:
            test_status_list = List(
                name="test_status",
                description="Test status list",
                created_by=sample_user.id,
                modified_by=sample_user.id
            )
            db_session.add(test_status_list)
            db_session.flush()
        
        in_process_status = ListEntry(
            list_id=test_status_list.id,
            name="In Process",
            description="Test in process",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(in_process_status)
        db_session.flush()
        
        complete_status = ListEntry(
            list_id=test_status_list.id,
            name="Complete",
            description="Test complete",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(complete_status)
        db_session.flush()
        
        sample_status_list = db_session.query(List).filter(List.name == "sample_status").first()
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
            list_id=sample_status_list.id,
            name="Received",
            description="Sample received",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(received_status)
        db_session.flush()
        
        sample_type = ListEntry(
            list_id=uuid4(),
            name="Water Sample",
            description="Water sample type",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(
            list_id=uuid4(),
            name="Water",
            description="Water matrix",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(matrix)
        db_session.flush()
        
        # Create container type
        container_type = ContainerType(
            name="Test Tube",
            description="Test tube",
            capacity=5.0,
            material="Plastic",
            dimensions="12x75",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container_type)
        db_session.flush()
        
        # Create containers and samples
        container1 = Container(
            name="Container 1",
            description="Test container 1",
            type_id=container_type.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(container1)
        db_session.flush()
        
        sample1 = Sample(
            name="SAMPLE-001",
            description="Test sample 1",
            project_id=project.id,
            sample_type=sample_type.id,
            status=received_status.id,
            matrix=matrix.id,
            temperature=25.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(sample1)
        db_session.flush()
        
        contents1 = Contents(
            container_id=container1.id,
            sample_id=sample1.id
        )
        db_session.add(contents1)
        db_session.flush()
        
        # Create analysis and analytes
        analysis = Analysis(
            name="pH Analysis",
            description="pH test",
            method="EPA Method 150.1",
            turnaround_time=1,
            cost=50.0,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis)
        db_session.flush()
        
        analyte1 = Analyte(
            name="pH",
            description="pH value",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte1)
        db_session.flush()
        
        analyte2 = Analyte(
            name="Temperature",
            description="Temperature",
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analyte2)
        db_session.flush()
        
        # Create analysis_analytes rules
        analysis_analyte1 = AnalysisAnalyte(
            analysis_id=analysis.id,
            analyte_id=analyte1.id,
            data_type="numeric",
            low_value=0.0,
            high_value=14.0,
            significant_figures=2,
            is_required=True,
            reported_name="pH",
            display_order=1,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis_analyte1)
        db_session.flush()
        
        analysis_analyte2 = AnalysisAnalyte(
            analysis_id=analysis.id,
            analyte_id=analyte2.id,
            data_type="numeric",
            low_value=-10.0,
            high_value=100.0,
            significant_figures=1,
            is_required=False,
            reported_name="Temperature",
            display_order=2,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(analysis_analyte2)
        db_session.flush()
        
        # Create test
        test1 = Test(
            sample_id=sample1.id,
            analysis_id=analysis.id,
            status=in_process_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(test1)
        db_session.flush()
        
        # Create batch
        batch = Batch(
            name="Test Batch",
            description="Test batch for results",
            status=batch_status.id,
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(batch)
        db_session.flush()
        
        # Link container to batch
        batch_container = BatchContainer(
            batch_id=batch.id,
            container_id=container1.id
        )
        db_session.add(batch_container)
        db_session.commit()
        
        # Enter batch results
        batch_results_data = {
            "batch_id": str(batch.id),
            "results": [
                {
                    "test_id": str(test1.id),
                    "analyte_results": [
                        {
                            "analyte_id": str(analyte1.id),
                            "raw_result": "7.5",
                            "reported_result": "7.5"
                        },
                        {
                            "analyte_id": str(analyte2.id),
                            "raw_result": "25.0",
                            "reported_result": "25"
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/results/batch", json=batch_results_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Test Batch"
        assert "containers" in data
        
        # Verify results were created
        results = db_session.query(Result).filter(
            Result.test_id == test1.id,
            Result.active == True
        ).all()
        assert len(results) == 2
        
        # Verify test status updated to Complete
        db_session.refresh(test1)
        assert test1.status == complete_status.id
    
    def test_enter_batch_results_validation_errors(self, db_session, auth_headers, sample_user):
        """Test batch results entry validation errors"""
        from models.batch import Batch, BatchContainer
        from models.container import Container, Contents, ContainerType
        from models.sample import Sample
        from models.test import Test
        from models.analysis import Analysis, Analyte, AnalysisAnalyte
        from models.project import Project
        from models.client import Client
        from models.list import List, ListEntry
        from datetime import datetime
        from uuid import uuid4
        
        # Create minimal test data (reuse from previous test setup)
        client_entity = Client(
            name="Test Client",
            description="Test client",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project",
            description="Test project",
            start_date=datetime.utcnow(),
            client_id=client_entity.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Get or create statuses (simplified)
        batch_status_list = db_session.query(List).filter(List.name == "batch_status").first()
        if not batch_status_list:
            batch_status_list = List(name="batch_status", description="Batch status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(batch_status_list)
            db_session.flush()
        
        batch_status = ListEntry(list_id=batch_status_list.id, name="Created", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(batch_status)
        db_session.flush()
        
        test_status_list = db_session.query(List).filter(List.name == "test_status").first()
        if not test_status_list:
            test_status_list = List(name="test_status", description="Test status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(test_status_list)
            db_session.flush()
        
        in_process_status = ListEntry(list_id=test_status_list.id, name="In Process", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(in_process_status)
        db_session.flush()
        
        sample_status_list = db_session.query(List).filter(List.name == "sample_status").first()
        if not sample_status_list:
            sample_status_list = List(name="sample_status", description="Sample status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(sample_status_list)
            db_session.flush()
        
        received_status = ListEntry(list_id=sample_status_list.id, name="Received", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(received_status)
        db_session.flush()
        
        sample_type = ListEntry(list_id=uuid4(), name="Water", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(list_id=uuid4(), name="Water", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(matrix)
        db_session.flush()
        
        container_type = ContainerType(name="Tube", capacity=5.0, material="Plastic", dimensions="12x75", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container_type)
        db_session.flush()
        
        container = Container(name="Container 1", type_id=container_type.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container)
        db_session.flush()
        
        sample = Sample(name="SAMPLE-001", project_id=project.id, sample_type=sample_type.id, status=received_status.id, matrix=matrix.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(sample)
        db_session.flush()
        
        contents = Contents(container_id=container.id, sample_id=sample.id)
        db_session.add(contents)
        db_session.flush()
        
        analysis = Analysis(name="pH", method="EPA", turnaround_time=1, cost=50.0, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(analysis)
        db_session.flush()
        
        analyte = Analyte(name="pH", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(analyte)
        db_session.flush()
        
        analysis_analyte = AnalysisAnalyte(
            analysis_id=analysis.id, analyte_id=analyte.id, data_type="numeric",
            low_value=0.0, high_value=14.0, is_required=True, reported_name="pH",
            display_order=1, created_by=sample_user.id, modified_by=sample_user.id
        )
        db_session.add(analysis_analyte)
        db_session.flush()
        
        test = Test(sample_id=sample.id, analysis_id=analysis.id, status=in_process_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(test)
        db_session.flush()
        
        batch = Batch(name="Test Batch", status=batch_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(batch)
        db_session.flush()
        
        batch_container = BatchContainer(batch_id=batch.id, container_id=container.id)
        db_session.add(batch_container)
        db_session.commit()
        
        # Try to enter invalid result (out of range)
        batch_results_data = {
            "batch_id": str(batch.id),
            "results": [
                {
                    "test_id": str(test.id),
                    "analyte_results": [
                        {
                            "analyte_id": str(analyte.id),
                            "raw_result": "15.0",  # Out of range (0-14)
                            "reported_result": "15.0"
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/results/batch", json=batch_results_data, headers=auth_headers)
        assert response.status_code == 400
        
        data = response.json()
        assert "errors" in data["detail"]
    
    def test_enter_batch_results_qc_block(self, db_session, auth_headers, sample_user, monkeypatch):
        """Test batch results entry with QC blocking enabled"""
        from models.batch import Batch, BatchContainer
        from models.container import Container, Contents, ContainerType
        from models.sample import Sample
        from models.test import Test
        from models.analysis import Analysis, Analyte, AnalysisAnalyte
        from models.project import Project
        from models.client import Client
        from models.list import List, ListEntry
        from datetime import datetime
        from uuid import uuid4
        
        # Enable QC blocking
        monkeypatch.setenv("FAIL_QC_BLOCKS_BATCH", "true")
        
        # Create test data (simplified setup)
        client_entity = Client(name="Test Client", billing_info={}, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(name="Test Project", start_date=datetime.utcnow(), client_id=client_entity.id, status=uuid4(), created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(project)
        db_session.flush()
        
        # Get or create QC type
        qc_types_list = db_session.query(List).filter(List.name == "qc_types").first()
        if not qc_types_list:
            qc_types_list = List(name="qc_types", description="QC types", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(qc_types_list)
            db_session.flush()
        
        blank_qc_type = ListEntry(list_id=qc_types_list.id, name="Blank", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(blank_qc_type)
        db_session.flush()
        
        batch_status_list = db_session.query(List).filter(List.name == "batch_status").first()
        if not batch_status_list:
            batch_status_list = List(name="batch_status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(batch_status_list)
            db_session.flush()
        
        batch_status = ListEntry(list_id=batch_status_list.id, name="Created", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(batch_status)
        db_session.flush()
        
        test_status_list = db_session.query(List).filter(List.name == "test_status").first()
        if not test_status_list:
            test_status_list = List(name="test_status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(test_status_list)
            db_session.flush()
        
        in_process_status = ListEntry(list_id=test_status_list.id, name="In Process", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(in_process_status)
        db_session.flush()
        
        sample_status_list = db_session.query(List).filter(List.name == "sample_status").first()
        if not sample_status_list:
            sample_status_list = List(name="sample_status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(sample_status_list)
            db_session.flush()
        
        received_status = ListEntry(list_id=sample_status_list.id, name="Received", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(received_status)
        db_session.flush()
        
        sample_type = ListEntry(list_id=uuid4(), name="Water", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(list_id=uuid4(), name="Water", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(matrix)
        db_session.flush()
        
        container_type = ContainerType(name="Tube", capacity=5.0, material="Plastic", dimensions="12x75", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container_type)
        db_session.flush()
        
        # Create regular sample
        container1 = Container(name="Container 1", type_id=container_type.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container1)
        db_session.flush()
        
        sample1 = Sample(name="SAMPLE-001", project_id=project.id, sample_type=sample_type.id, status=received_status.id, matrix=matrix.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(sample1)
        db_session.flush()
        
        contents1 = Contents(container_id=container1.id, sample_id=sample1.id)
        db_session.add(contents1)
        db_session.flush()
        
        # Create QC sample
        container_qc = Container(name="QC Container", type_id=container_type.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container_qc)
        db_session.flush()
        
        qc_sample = Sample(name="QC-001", project_id=project.id, sample_type=sample_type.id, status=received_status.id, matrix=matrix.id, qc_type=blank_qc_type.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(qc_sample)
        db_session.flush()
        
        contents_qc = Contents(container_id=container_qc.id, sample_id=qc_sample.id)
        db_session.add(contents_qc)
        db_session.flush()
        
        analysis = Analysis(name="pH", method="EPA", turnaround_time=1, cost=50.0, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(analysis)
        db_session.flush()
        
        analyte = Analyte(name="pH", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(analyte)
        db_session.flush()
        
        analysis_analyte = AnalysisAnalyte(
            analysis_id=analysis.id, analyte_id=analyte.id, data_type="numeric",
            low_value=0.0, high_value=14.0, is_required=True, reported_name="pH",
            display_order=1, created_by=sample_user.id, modified_by=sample_user.id
        )
        db_session.add(analysis_analyte)
        db_session.flush()
        
        test1 = Test(sample_id=sample1.id, analysis_id=analysis.id, status=in_process_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(test1)
        db_session.flush()
        
        # QC test with no results (will trigger QC failure)
        qc_test = Test(sample_id=qc_sample.id, analysis_id=analysis.id, status=in_process_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(qc_test)
        db_session.flush()
        
        batch = Batch(name="Test Batch", status=batch_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(batch)
        db_session.flush()
        
        batch_container1 = BatchContainer(batch_id=batch.id, container_id=container1.id)
        db_session.add(batch_container1)
        batch_container_qc = BatchContainer(batch_id=batch.id, container_id=container_qc.id)
        db_session.add(batch_container_qc)
        db_session.commit()
        
        # Try to enter results (QC test has no results, should block)
        batch_results_data = {
            "batch_id": str(batch.id),
            "results": [
                {
                    "test_id": str(test1.id),
                    "analyte_results": [
                        {
                            "analyte_id": str(analyte.id),
                            "raw_result": "7.5",
                            "reported_result": "7.5"
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/results/batch", json=batch_results_data, headers=auth_headers)
        assert response.status_code == 400
        
        data = response.json()
        assert "qc_failures" in data["detail"]
    
    def test_enter_batch_results_end_to_end_with_qc_and_status_update(self, db_session, auth_headers, sample_user):
        """End-to-end test: Batch results entry with QC, validation, and batch status update"""
        from models.batch import Batch, BatchContainer
        from models.container import Container, Contents, ContainerType
        from models.sample import Sample
        from models.test import Test
        from models.analysis import Analysis, Analyte, AnalysisAnalyte
        from models.project import Project
        from models.client import Client
        from models.list import List, ListEntry
        from datetime import datetime
        from uuid import uuid4
        
        # Create client and project
        client_entity = Client(
            name="Test Client E2E",
            description="Test client for E2E",
            billing_info={},
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(client_entity)
        db_session.flush()
        
        project = Project(
            name="Test Project E2E",
            description="Test project for E2E",
            start_date=datetime.utcnow(),
            client_id=client_entity.id,
            status=uuid4(),
            created_by=sample_user.id,
            modified_by=sample_user.id
        )
        db_session.add(project)
        db_session.flush()
        
        # Get or create list entries
        batch_status_list = db_session.query(List).filter(List.name == "batch_status").first()
        if not batch_status_list:
            batch_status_list = List(name="batch_status", description="Batch status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(batch_status_list)
            db_session.flush()
        
        created_status = ListEntry(list_id=batch_status_list.id, name="Created", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(created_status)
        db_session.flush()
        
        completed_status = ListEntry(list_id=batch_status_list.id, name="Completed", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(completed_status)
        db_session.flush()
        
        test_status_list = db_session.query(List).filter(List.name == "test_status").first()
        if not test_status_list:
            test_status_list = List(name="test_status", description="Test status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(test_status_list)
            db_session.flush()
        
        in_process_status = ListEntry(list_id=test_status_list.id, name="In Process", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(in_process_status)
        db_session.flush()
        
        complete_status = ListEntry(list_id=test_status_list.id, name="Complete", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(complete_status)
        db_session.flush()
        
        sample_status_list = db_session.query(List).filter(List.name == "sample_status").first()
        if not sample_status_list:
            sample_status_list = List(name="sample_status", description="Sample status", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(sample_status_list)
            db_session.flush()
        
        received_status = ListEntry(list_id=sample_status_list.id, name="Received", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(received_status)
        db_session.flush()
        
        qc_types_list = db_session.query(List).filter(List.name == "qc_types").first()
        if not qc_types_list:
            qc_types_list = List(name="qc_types", description="QC types", created_by=sample_user.id, modified_by=sample_user.id)
            db_session.add(qc_types_list)
            db_session.flush()
        
        blank_qc_type = ListEntry(list_id=qc_types_list.id, name="Blank", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(blank_qc_type)
        db_session.flush()
        
        sample_type = ListEntry(list_id=uuid4(), name="Water", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(sample_type)
        db_session.flush()
        
        matrix = ListEntry(list_id=uuid4(), name="Water", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(matrix)
        db_session.flush()
        
        container_type = ContainerType(name="Tube", capacity=5.0, material="Plastic", dimensions="12x75", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container_type)
        db_session.flush()
        
        # Create regular sample
        container1 = Container(name="Container 1", type_id=container_type.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container1)
        db_session.flush()
        
        sample1 = Sample(name="SAMPLE-001", project_id=project.id, sample_type=sample_type.id, status=received_status.id, matrix=matrix.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(sample1)
        db_session.flush()
        
        contents1 = Contents(container_id=container1.id, sample_id=sample1.id)
        db_session.add(contents1)
        db_session.flush()
        
        # Create QC sample
        container_qc = Container(name="QC Container", type_id=container_type.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(container_qc)
        db_session.flush()
        
        qc_sample = Sample(name="QC-001", project_id=project.id, sample_type=sample_type.id, status=received_status.id, matrix=matrix.id, qc_type=blank_qc_type.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(qc_sample)
        db_session.flush()
        
        contents_qc = Contents(container_id=container_qc.id, sample_id=qc_sample.id)
        db_session.add(contents_qc)
        db_session.flush()
        
        # Create analysis and analytes
        analysis = Analysis(name="pH Analysis", method="EPA", turnaround_time=1, cost=50.0, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(analysis)
        db_session.flush()
        
        analyte1 = Analyte(name="pH", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(analyte1)
        db_session.flush()
        
        analyte2 = Analyte(name="Temperature", created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(analyte2)
        db_session.flush()
        
        analysis_analyte1 = AnalysisAnalyte(
            analysis_id=analysis.id, analyte_id=analyte1.id, data_type="numeric",
            low_value=0.0, high_value=14.0, is_required=True, reported_name="pH",
            display_order=1, created_by=sample_user.id, modified_by=sample_user.id
        )
        db_session.add(analysis_analyte1)
        db_session.flush()
        
        analysis_analyte2 = AnalysisAnalyte(
            analysis_id=analysis.id, analyte_id=analyte2.id, data_type="numeric",
            low_value=-10.0, high_value=100.0, is_required=False, reported_name="Temperature",
            display_order=2, created_by=sample_user.id, modified_by=sample_user.id
        )
        db_session.add(analysis_analyte2)
        db_session.flush()
        
        # Create tests
        test1 = Test(sample_id=sample1.id, analysis_id=analysis.id, status=in_process_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(test1)
        db_session.flush()
        
        qc_test = Test(sample_id=qc_sample.id, analysis_id=analysis.id, status=in_process_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(qc_test)
        db_session.flush()
        
        # Create batch
        batch = Batch(name="E2E Test Batch", status=created_status.id, created_by=sample_user.id, modified_by=sample_user.id)
        db_session.add(batch)
        db_session.flush()
        
        batch_container1 = BatchContainer(batch_id=batch.id, container_id=container1.id)
        db_session.add(batch_container1)
        batch_container_qc = BatchContainer(batch_id=batch.id, container_id=container_qc.id)
        db_session.add(batch_container_qc)
        db_session.commit()
        
        # Enter results for both tests
        batch_results_data = {
            "batch_id": str(batch.id),
            "results": [
                {
                    "test_id": str(test1.id),
                    "analyte_results": [
                        {
                            "analyte_id": str(analyte1.id),
                            "raw_result": "7.5",
                            "reported_result": "7.5"
                        },
                        {
                            "analyte_id": str(analyte2.id),
                            "raw_result": "25.0",
                            "reported_result": "25"
                        }
                    ]
                },
                {
                    "test_id": str(qc_test.id),
                    "analyte_results": [
                        {
                            "analyte_id": str(analyte1.id),
                            "raw_result": "7.0",
                            "reported_result": "7.0"
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/results/batch", json=batch_results_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "E2E Test Batch"
        
        # Verify batch status updated to Completed
        db_session.refresh(batch)
        assert batch.status == completed_status.id
        assert batch.end_date is not None
        
        # Verify test statuses updated to Complete
        db_session.refresh(test1)
        db_session.refresh(qc_test)
        assert test1.status == complete_status.id
        assert qc_test.status == complete_status.id
        
        # Verify results were created
        results = db_session.query(Result).filter(
            Result.test_id.in_([test1.id, qc_test.id]),
            Result.active == True
        ).all()
        assert len(results) >= 3  # At least 3 results (2 for test1, 1 for qc_test)