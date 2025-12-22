import React from 'react';
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
} from '@mui/material';
import {
  CheckCircle,
  Science,
  Assignment,
  Storage,
} from '@mui/icons-material';

interface ReviewStepProps {
  values: any;
  lookupData: {
    sampleTypes: any[];
    statuses: any[];
    matrices: any[];
    qcTypes: any[];
    projects: any[];
    analyses: any[];
    containerTypes: any[];
    units: any[];
  };
}

const ReviewStep: React.FC<ReviewStepProps> = ({ values, lookupData }) => {
  const getLookupName = (id: string, list: any[]) => {
    const item = list.find(item => item.id === id);
    return item ? item.name : 'Unknown';
  };

  const selectedAnalyses = lookupData.analyses.filter(analysis => 
    values.selected_analyses?.includes(analysis.id)
  );

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Review Sample Information
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Please review all information before submitting. This will create the sample, container, and associated tests.
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
                <ListItem>
                  <ListItemText
                    primary="Name"
                    secondary={values.name}
                  />
                </ListItem>
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
                <ListItem>
                  <ListItemText
                    primary="Temperature"
                    secondary={`${values.temperature}°C`}
                  />
                </ListItem>
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
                    primary="Project"
                    secondary={getLookupName(values.project_id, lookupData.projects)}
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

        {/* Test Assignment */}
        <Grid size={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Assignment sx={{ mr: 1, verticalAlign: 'middle' }} />
                Test Assignment
              </Typography>
              
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
        {values.double_entry_enabled && (
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
