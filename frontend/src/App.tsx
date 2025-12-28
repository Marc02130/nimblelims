import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import AccessioningForm from './pages/AccessioningForm';
import ContainerManagement from './pages/ContainerManagement';
import BatchManagement from './pages/BatchManagement';
import ResultsManagement from './pages/ResultsManagement';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import ListsManagement from './pages/admin/ListsManagement';
import ContainerTypesManagement from './pages/admin/ContainerTypesManagement';
import UsersManagement from './pages/admin/UsersManagement';
import RolesManagement from './pages/admin/RolesManagement';
import AnalysesManagement from './pages/admin/AnalysesManagement';
import TestBatteriesManagement from './pages/admin/TestBatteriesManagement';
import AnalytesManagement from './pages/admin/AnalytesManagement';
import AnalysisAnalytesConfig from './pages/admin/AnalysisAnalytesConfig';
import ClientProjects from './pages/ClientProjects';
import { useUser } from './contexts/UserContext';

function AppRoutes() {
  const { user } = useUser();
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith('/admin');

  // Admin routes have their own layout (AdminDashboard handles it)
  if (isAdminRoute) {
    return (
      <Routes>
        <Route
          path="/admin"
          element={
            user && user.permissions.includes('config:edit') ? (
              <AdminDashboard />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        >
          <Route path="lists" element={<ListsManagement />} />
          <Route path="container-types" element={<ContainerTypesManagement />} />
          <Route path="users" element={<UsersManagement />} />
          <Route path="roles" element={<RolesManagement />} />
          <Route path="analyses" element={<AnalysesManagement />} />
          <Route path="analyses/:analysisId/analytes" element={<AnalysisAnalytesConfig />} />
          <Route path="analytes" element={<AnalytesManagement />} />
          <Route path="test-batteries" element={<TestBatteriesManagement />} />
        </Route>
      </Routes>
    );
  }

  // Regular routes with Navbar
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/accessioning" element={<AccessioningForm />} />
          <Route path="/containers" element={<ContainerManagement />} />
          <Route path="/batches" element={<BatchManagement />} />
          <Route path="/results" element={<ResultsManagement />} />
          <Route path="/client-projects" element={<ClientProjects />} />
        </Routes>
      </Box>
    </Box>
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
