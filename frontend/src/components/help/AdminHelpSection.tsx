import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { apiService } from '../../services/apiService';

interface HelpEntry {
  id: string;
  section: string;
  content: string;
  role_filter: string | null;
  active: boolean;
}

const AdminHelpSection: React.FC = () => {
  const [helpEntries, setHelpEntries] = useState<HelpEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | false>(false);

  useEffect(() => {
    const fetchHelp = async () => {
      try {
        setLoading(true);
        setError(null);
        // Fetch administrator help entries
        // Backend converts "Administrator" role name to "administrator" slug format
        const response = await apiService.getHelp({ role: 'administrator' });
        // Handle both array and paginated response
        const entries = response.help_entries || response || [];
        setHelpEntries(entries);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load help content');
      } finally {
        setLoading(false);
      }
    };

    fetchHelp();
  }, []);

  const handleAccordionChange = (section: string) => (
    event: React.SyntheticEvent,
    isExpanded: boolean
  ) => {
    setExpanded(isExpanded ? section : false);
  };

  if (loading) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        minHeight={200}
        aria-live="polite"
        aria-label="Loading help content"
      >
        <CircularProgress aria-label="Loading" />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert 
        severity="error" 
        sx={{ mb: 2 }}
        role="alert"
        aria-live="assertive"
      >
        {error}
      </Alert>
    );
  }

  if (helpEntries.length === 0) {
    return (
      <Paper 
        sx={{ p: 3, textAlign: 'center' }}
        role="status"
        aria-live="polite"
      >
        <Typography variant="body1" color="text.secondary">
          No help content available at this time.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Typography 
        variant="h5" 
        component="h2" 
        gutterBottom 
        sx={{ mb: 3 }}
        id="admin-help-heading"
      >
        Help & Support
      </Typography>
      <Typography 
        variant="body2" 
        color="text.secondary" 
        paragraph 
        sx={{ mb: 3 }}
      >
        Find answers to common questions about system administration in NimbleLIMS. 
        Click on a topic below to learn more.
      </Typography>
      <Box 
        component="nav"
        aria-labelledby="admin-help-heading"
        role="navigation"
      >
        {helpEntries.map((entry) => (
          <Accordion
            key={entry.id}
            expanded={expanded === entry.section}
            onChange={handleAccordionChange(entry.section)}
            sx={{
              mb: 1,
              '&:before': {
                display: 'none',
              },
              boxShadow: 1,
            }}
            aria-expanded={expanded === entry.section}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon aria-hidden="true" />}
              aria-controls={`${entry.section}-content`}
              id={`${entry.section}-header`}
              aria-label={`${entry.section} help section`}
              sx={{
                '& .MuiAccordionSummary-content': {
                  my: 1.5,
                },
              }}
            >
              <Typography 
                variant="h6" 
                component="h3" 
                sx={{ fontWeight: 500 }}
              >
                {entry.section}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              id={`${entry.section}-content`}
              role="region"
              aria-labelledby={`${entry.section}-header`}
            >
              <Typography
                variant="body1"
                component="div"
                sx={{
                  whiteSpace: 'pre-line',
                  lineHeight: 1.7,
                  color: 'text.primary',
                }}
              >
                {entry.content}
              </Typography>
              {entry.section === 'EAV Configuration' && (
                <Box sx={{ mt: 2, p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                  <Typography variant="body2" color="info.dark">
                    <strong>Tip:</strong> Custom Attributes: Edit configs (post-MVP EAV). 
                    Use the Custom Fields Management page to configure EAV attributes.
                  </Typography>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>
    </Box>
  );
};

export default AdminHelpSection;

