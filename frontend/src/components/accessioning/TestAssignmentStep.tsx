import React from 'react';
import {
  Box,
  Grid,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  FormControlLabel,
  Checkbox,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';

interface TestAssignmentStepProps {
  values: any;
  setFieldValue: (field: string, value: any) => void;
  lookupData: {
    analyses: any[];
  };
}

const TestAssignmentStep: React.FC<TestAssignmentStepProps> = ({
  values,
  setFieldValue,
  lookupData,
}) => {
  const handleAnalysisToggle = (analysisId: string) => {
    const currentAnalyses = values.selected_analyses || [];
    const isSelected = currentAnalyses.includes(analysisId);
    
    if (isSelected) {
      setFieldValue('selected_analyses', currentAnalyses.filter((id: string) => id !== analysisId));
    } else {
      setFieldValue('selected_analyses', [...currentAnalyses, analysisId]);
    }
  };

  const selectedAnalyses = lookupData.analyses.filter(analysis => 
    values.selected_analyses?.includes(analysis.id)
  );

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Test Assignment
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Select the analyses to be performed on this sample. Tests will be created automatically.
      </Typography>

      <Grid container spacing={2}>
        {lookupData.analyses.map((analysis) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={analysis.id}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                border: values.selected_analyses?.includes(analysis.id) ? 2 : 1,
                borderColor: values.selected_analyses?.includes(analysis.id) ? 'primary.main' : 'divider',
                '&:hover': {
                  borderColor: 'primary.main',
                }
              }}
              onClick={() => handleAnalysisToggle(analysis.id)}
            >
              <CardContent>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={values.selected_analyses?.includes(analysis.id) || false}
                      onChange={() => handleAnalysisToggle(analysis.id)}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {analysis.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Method: {analysis.method}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Turnaround: {analysis.turnaround_time} days
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Cost: ${analysis.cost}
                      </Typography>
                    </Box>
                  }
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {selectedAnalyses.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Selected Analyses ({selectedAnalyses.length})
          </Typography>
          
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            {selectedAnalyses.map((analysis) => (
              <Chip
                key={analysis.id}
                label={analysis.name}
                onDelete={() => handleAnalysisToggle(analysis.id)}
                color="primary"
                variant="outlined"
              />
            ))}
          </Box>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Analysis Summary
              </Typography>
              <List dense>
                {selectedAnalyses.map((analysis) => (
                  <ListItem key={analysis.id}>
                    <ListItemText
                      primary={analysis.name}
                      secondary={`${analysis.method} • ${analysis.turnaround_time} days • $${analysis.cost}`}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Box>
      )}

      {lookupData.analyses.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">
            No analyses available. Please contact your administrator.
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default TestAssignmentStep;
