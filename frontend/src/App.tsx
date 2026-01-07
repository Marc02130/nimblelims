import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import AccessioningForm from './pages/AccessioningForm';
import SamplesManagement from './pages/SamplesManagement';
import TestsManagement from './pages/TestsManagement';
import ContainerManagement from './pages/ContainerManagement';
import BatchManagement from './pages/BatchManagement';
import ResultsManagement from './pages/ResultsManagement';
import Login from './pages/Login';
import AdminOverview from './pages/admin/AdminOverview';
import ListsManagement from './pages/admin/ListsManagement';
import ContainerTypesManagement from './pages/admin/ContainerTypesManagement';
import UnitsManagement from './pages/admin/UnitsManagement';
import UsersManagement from './pages/admin/UsersManagement';
import RolesManagement from './pages/admin/RolesManagement';
import AnalysesManagement from './pages/admin/AnalysesManagement';
import TestBatteriesManagement from './pages/admin/TestBatteriesManagement';
import AnalytesManagement from './pages/admin/AnalytesManagement';
import AnalysisAnalytesConfig from './pages/admin/AnalysisAnalytesConfig';
import CustomFieldsManagement from './pages/admin/CustomFieldsManagement';
import HelpManagement from './pages/admin/HelpManagement';
import ClientProjects from './pages/ClientProjects';
import ClientsManagement from './pages/ClientsManagement';
import HelpPage from './pages/HelpPage';
import { useUser } from './contexts/UserContext';

function AppRoutes() {
  const { user, hasPermission } = useUser();

  return (
    <MainLayout>
      <Routes>
        {/* Root redirect */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Core Features Routes */}
        <Route path="/dashboard" element={<Dashboard />} />
        <Route
          path="/accessioning"
          element={
            hasPermission('sample:create') ? (
              <AccessioningForm />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/samples"
          element={
            hasPermission('sample:read') ? (
              <SamplesManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/samples/:id"
          element={
            hasPermission('sample:update') ? (
              <SamplesManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/tests"
          element={
            hasPermission('test:update') ? (
              <TestsManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/tests/:id"
          element={
            hasPermission('test:update') ? (
              <TestsManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/containers"
          element={
            hasPermission('sample:update') ? (
              <ContainerManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/containers/:id"
          element={
            hasPermission('sample:update') ? (
              <ContainerManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/batches"
          element={
            hasPermission('batch:manage') ? (
              <BatchManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/results"
          element={
            hasPermission('result:enter') ? (
              <ResultsManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/client-projects"
          element={
            hasPermission('project:manage') ? (
              <ClientProjects />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/clients"
          element={
            hasPermission('project:manage') ? (
              <ClientsManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route path="/help" element={<HelpPage />} />

        {/* Admin Routes */}
        <Route
          path="/admin"
          element={
            hasPermission('config:edit') ? (
              <AdminOverview />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/lists"
          element={
            hasPermission('config:edit') ? (
              <ListsManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/container-types"
          element={
            hasPermission('config:edit') ? (
              <ContainerTypesManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/units"
          element={
            hasPermission('config:edit') ? (
              <UnitsManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/users"
          element={
            hasPermission('config:edit') || hasPermission('user:manage') ? (
              <UsersManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/roles"
          element={
            hasPermission('config:edit') || hasPermission('user:manage') ? (
              <RolesManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/analyses"
          element={
            hasPermission('config:edit') || hasPermission('test:configure') ? (
              <AnalysesManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/analyses/:analysisId/analytes"
          element={
            hasPermission('config:edit') || hasPermission('test:configure') ? (
              <AnalysisAnalytesConfig />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/analytes"
          element={
            hasPermission('config:edit') || hasPermission('test:configure') ? (
              <AnalytesManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/test-batteries"
          element={
            hasPermission('config:edit') || hasPermission('test:configure') ? (
              <TestBatteriesManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/custom-fields"
          element={
            hasPermission('config:edit') ? (
              <CustomFieldsManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/admin/help"
          element={
            hasPermission('config:edit') ? (
              <HelpManagement />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
      </Routes>
    </MainLayout>
  );
}

function App() {
  const { user, loading } = useUser();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Login />;
  }

  return <AppRoutes />;
}

export default App;
