import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import AccessioningForm from './pages/AccessioningForm';
import ContainerManagement from './pages/ContainerManagement';
import BatchManagement from './pages/BatchManagement';
import ResultsManagement from './pages/ResultsManagement';
import Login from './pages/Login';
import { useUser } from './contexts/UserContext';

function App() {
  const { user, loading } = useUser();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Login />;
  }

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
        </Routes>
      </Box>
    </Box>
  );
}

export default App;
