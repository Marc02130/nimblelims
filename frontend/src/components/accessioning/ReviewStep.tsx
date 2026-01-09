import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle,
  Science,
  Assignment,
  Storage,
  AutoAwesome,
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';

interface ReviewStepProps {
  values: any;
  lookupData: {
    sampleTypes: any[];
    statuses: any[];
    matrices: any[];
    qcTypes: any[];
    projects: any[];
    clients: any[];
    clientProjects: any[];
    analyses: any[];
    batteries: any[];
    containerTypes: any[];
    units: any[];
  };
  bulkMode?: boolean;
}

const ReviewStep: React.FC<ReviewStepProps> = ({ values, lookupData, bulkMode = false }) => {
  const [projectPreview, setProjectPreview] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    if (values.client_id && values.received_date) {
      loadProjectPreview();
    } else {
      setProjectPreview(null);
    }
  }, [values.client_id, values.received_date]);

  const loadProjectPreview = async () => {
    try {
      setLoadingPreview(true);
      // Try to get project name preview from API
      try {
        const response = await apiService.getGeneratedNamePreview('project', values.client_id, values.received_date);
        setProjectPreview(response || null);
      } catch (err) {
        // If preview endpoint doesn't exist, generate locally
        const client = lookupData.clients?.find((c: any) => c.id === values.client_id);
        if (client) {
          const clientName = client.name || 'UNKNOWN';
          const clientCode = clientName.toUpperCase().replace(/[^A-Z0-9]/g, '').substring(0, 10);
          const date = values.received_date ? new Date(values.received_date) : new Date();
          const dateStr = date.toISOString().split('T')[0].replace(/-/g, '');
          setProjectPreview(`PROJ-${clientCode}-${dateStr}-001`);
        } else {
          setProjectPreview(null);
        }
      }
    } catch (err: any) {
      console.error('Error loading project preview:', err);
      setProjectPreview(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  const getLookupName = (id: string, list: any[]) => {
    const item = list.find(item => item.id === id);
    return item ? item.name : 'Unknown';
  };

  const getClientName = () => {
    if (values.client_id) {
      return getLookupName(values.client_id, lookupData.clients || []);
    }
    return 'Not selected';
  };

  const getClientProjectName = () => {
    if (values.client_project_id) {
      const clientProject = lookupData.clientProjects?.find((cp: any) => cp.id === values.client_project_id);
      return clientProject ? clientProject.name : 'Unknown';
    }
    return 'None';
  };

  const selectedAnalyses = lookupData.analyses.filter(analysis => 
    values.selected_analyses?.includes(analysis.id)
  );

  const selectedBattery = lookupData.batteries?.find((b: any) => b.id === values.battery_id);

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Review Sample Information
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Please review all information before submitting. This will create the sample, container, and associated tests.
        {!values.project_id && (
          <Typography component="span" variant="body2" sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}>
            A new project will be automatically created for the selected client.
          </Typography>
        )}
      </Typography>

      <Grid container spacing={3}>
        {/* Sample Information */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Science sx={{ mr: 1, verticalAlign: 'middle' }} />
                Sample Details
              </Typography>
              
              <List dense>
                {!bulkMode && (
                <ListItem>
                  <ListItemText
                    primary="Name"
                      secondary={values.auto_generate_name ? '(Auto-generated)' : values.name || 'Not specified'}
                  />
                </ListItem>
                )}
                <ListItem>
                  <ListItemText
                    primary="Description"
                    secondary={values.description || 'None'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Sample Type"
                    secondary={getLookupName(values.sample_type, lookupData.sampleTypes)}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Status"
                    secondary={getLookupName(values.status, lookupData.statuses)}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Matrix"
                    secondary={getLookupName(values.matrix, lookupData.matrices)}
                  />
                </ListItem>
                {!bulkMode && (
                <ListItem>
                  <ListItemText
                    primary="Temperature"
                    secondary={`${values.temperature}°C`}
                  />
                </ListItem>
                )}
                <ListItem>
                  <ListItemText
                    primary="Due Date"
                    secondary={values.due_date}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Received Date"
                    secondary={values.received_date}
                  />
                </ListItem>
                {values.qc_type && (
                  <ListItem>
                    <ListItemText
                      primary="QC Type"
                      secondary={getLookupName(values.qc_type, lookupData.qcTypes)}
                    />
                  </ListItem>
                )}
                <ListItem>
                  <ListItemText
                    primary="Client"
                    secondary={getClientName()}
                  />
                </ListItem>
                {values.client_project_id && (
                  <ListItem>
                    <ListItemText
                      primary="Client Project"
                      secondary={getClientProjectName()}
                    />
                  </ListItem>
                )}
                <ListItem>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography component="span">Project</Typography>
                        <AutoAwesome fontSize="small" color="primary" />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography component="span" sx={{ fontWeight: 'medium' }}>
                          Auto-Created
                        </Typography>
                        {projectPreview && (
                          <Typography component="span" variant="caption" sx={{ display: 'block', mt: 0.5, fontStyle: 'italic' }}>
                            Preview: {projectPreview}
                          </Typography>
                        )}
                        {loadingPreview && (
                          <CircularProgress size={12} sx={{ ml: 1 }} />
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {values.anomalies && (
                  <ListItem>
                    <ListItemText
                      primary="Anomalies/Notes"
                      secondary={values.anomalies}
                    />
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Container Information */}
        {!bulkMode && (
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Storage sx={{ mr: 1, verticalAlign: 'middle' }} />
                Container Details
              </Typography>
              
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Container Name/Barcode"
                    secondary={values.container_name || 'Not specified'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Container Type"
                    secondary={getLookupName(values.container_type_id, lookupData.containerTypes)}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Row/Column"
                    secondary={`Row: ${values.container_row || 1}, Column: ${values.container_column || 1}`}
                  />
                </ListItem>
                {values.container_concentration !== null && values.container_concentration !== undefined && (
                  <ListItem>
                    <ListItemText
                      primary="Concentration"
                      secondary={`${values.container_concentration} ${values.container_concentration_units ? getLookupName(values.container_concentration_units, lookupData.units) : ''}`}
                    />
                  </ListItem>
                )}
                {values.container_amount !== null && values.container_amount !== undefined && (
                <ListItem>
                  <ListItemText
                    primary="Amount"
                      secondary={`${values.container_amount} ${values.container_amount_units ? getLookupName(values.container_amount_units, lookupData.units) : ''}`}
                  />
                </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
        )}

        {/* Bulk Mode Container Info */}
        {bulkMode && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <Storage sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Container Information
                </Typography>
                
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Container Type"
                      secondary={getLookupName(values.container_type_id, lookupData.containerTypes)}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Number of Samples"
                      secondary={values.bulk_uniques?.length || 0}
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Test Assignment */}
        <Grid size={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Assignment sx={{ mr: 1, verticalAlign: 'middle' }} />
                Test Assignment
              </Typography>
              
              {selectedBattery && (
                <Box sx={{ mb: 2 }}>
                  <Chip
                    label={`Battery: ${selectedBattery.name}`}
                    color="primary"
                    variant="outlined"
                    icon={<CheckCircle />}
                  />
                </Box>
              )}
              
              {selectedAnalyses.length > 0 ? (
                <Box>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                    {selectedAnalyses.map((analysis) => (
                      <Chip
                        key={analysis.id}
                        label={analysis.name}
                        color="primary"
                        icon={<CheckCircle />}
                      />
                    ))}
                  </Box>
                  
                  <List dense>
                    {selectedAnalyses.map((analysis) => (
                      <ListItem key={analysis.id}>
                        <ListItemIcon>
                          <CheckCircle color="primary" />
                        </ListItemIcon>
                        <ListItemText
                          primary={analysis.name}
                          secondary={`${analysis.method} • ${analysis.turnaround_time} days • $${analysis.cost}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              ) : (
                <Typography color="text.secondary">
                  No tests assigned to this sample.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Double Entry Validation */}
        {!bulkMode && values.double_entry_enabled && (
          <Grid size={12}>
            <Card variant="outlined" sx={{ bgcolor: 'action.hover' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Double Entry Validation
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="body2" color="text.secondary">
                      Original Name: {values.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Verified Name: {values.name_verification}
                    </Typography>
                    {values.name === values.name_verification ? (
                      <Chip label="Match" color="success" size="small" />
                    ) : (
                      <Chip label="Mismatch" color="error" size="small" />
                    )}
                  </Grid>
                  
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="body2" color="text.secondary">
                      Original Type: {getLookupName(values.sample_type, lookupData.sampleTypes)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Verified Type: {getLookupName(values.sample_type_verification, lookupData.sampleTypes)}
                    </Typography>
                    {values.sample_type === values.sample_type_verification ? (
                      <Chip label="Match" color="success" size="small" />
                    ) : (
                      <Chip label="Mismatch" color="error" size="small" />
                    )}
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default ReviewStep;
