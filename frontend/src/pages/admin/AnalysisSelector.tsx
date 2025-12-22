import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Checkbox,
  FormControlLabel,
  IconButton,
  Paper,
  Chip,
  Button,
} from '@mui/material';
import {
  DragIndicator,
  Delete,
  Add,
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';

interface Analysis {
  id: string;
  name: string;
  method?: string;
  description?: string;
}

interface BatteryAnalysis {
  analysis_id: string;
  analysis_name: string;
  analysis_method?: string;
  sequence: number;
  optional: boolean;
}

interface AnalysisSelectorProps {
  selectedAnalyses: BatteryAnalysis[];
  onChange: (analyses: BatteryAnalysis[]) => void;
  error?: string;
}

const AnalysisSelector: React.FC<AnalysisSelectorProps> = ({
  selectedAnalyses,
  onChange,
  error,
}) => {
  const [allAnalyses, setAllAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [availableAnalyses, setAvailableAnalyses] = useState<Analysis[]>([]);

  useEffect(() => {
    loadAnalyses();
  }, []);

  useEffect(() => {
    // Filter out already selected analyses
    const selectedIds = new Set(selectedAnalyses.map(a => a.analysis_id));
    setAvailableAnalyses(allAnalyses.filter(a => !selectedIds.has(a.id)));
  }, [allAnalyses, selectedAnalyses]);

  const loadAnalyses = async () => {
    try {
      setLoading(true);
      const analyses = await apiService.getAnalyses();
      setAllAnalyses(analyses || []);
    } catch (err: any) {
      console.error('Failed to load analyses:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAnalysis = () => {
    if (availableAnalyses.length === 0) return;
    
    const newAnalysis = availableAnalyses[0];
    const maxSequence = selectedAnalyses.length > 0
      ? Math.max(...selectedAnalyses.map(a => a.sequence))
      : 0;
    
    const newBatteryAnalysis: BatteryAnalysis = {
      analysis_id: newAnalysis.id,
      analysis_name: newAnalysis.name,
      analysis_method: newAnalysis.method,
      sequence: maxSequence + 1,
      optional: false,
    };
    
    onChange([...selectedAnalyses, newBatteryAnalysis]);
  };

  const handleRemoveAnalysis = (analysisId: string) => {
    const updated = selectedAnalyses
      .filter(a => a.analysis_id !== analysisId)
      .map((a, index) => ({ ...a, sequence: index + 1 }));
    onChange(updated);
  };

  const handleSequenceChange = (analysisId: string, newSequence: number) => {
    if (newSequence < 1) return;
    
    const updated = [...selectedAnalyses];
    const index = updated.findIndex(a => a.analysis_id === analysisId);
    if (index === -1) return;
    
    const oldSequence = updated[index].sequence;
    updated[index].sequence = newSequence;
    
    // Reorder other analyses
    updated.forEach((a, i) => {
      if (i !== index) {
        if (oldSequence < newSequence) {
          // Moving down
          if (a.sequence > oldSequence && a.sequence <= newSequence) {
            a.sequence -= 1;
          }
        } else {
          // Moving up
          if (a.sequence >= newSequence && a.sequence < oldSequence) {
            a.sequence += 1;
          }
        }
      }
    });
    
    // Sort by sequence
    updated.sort((a, b) => a.sequence - b.sequence);
    onChange(updated);
  };

  const handleOptionalToggle = (analysisId: string, optional: boolean) => {
    const updated = selectedAnalyses.map(a =>
      a.analysis_id === analysisId ? { ...a, optional } : a
    );
    onChange(updated);
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const updated = [...selectedAnalyses];
    [updated[index - 1], updated[index]] = [updated[index], updated[index - 1]];
    updated.forEach((a, i) => {
      a.sequence = i + 1;
    });
    onChange(updated);
  };

  const handleMoveDown = (index: number) => {
    if (index === selectedAnalyses.length - 1) return;
    const updated = [...selectedAnalyses];
    [updated[index], updated[index + 1]] = [updated[index + 1], updated[index]];
    updated.forEach((a, i) => {
      a.sequence = i + 1;
    });
    onChange(updated);
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="subtitle2" color="textSecondary">
          Analyses in Battery ({selectedAnalyses.length})
        </Typography>
        <Button
          size="small"
          startIcon={<Add />}
          onClick={handleAddAnalysis}
          disabled={availableAnalyses.length === 0 || loading}
        >
          Add Analysis
        </Button>
      </Box>

      {error && (
        <Typography variant="caption" color="error" sx={{ mb: 1, display: 'block' }}>
          {error}
        </Typography>
      )}

      {selectedAnalyses.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="textSecondary">
            No analyses selected. Click "Add Analysis" to add analyses to this battery.
          </Typography>
        </Paper>
      ) : (
        <Box>
          {selectedAnalyses
            .sort((a, b) => a.sequence - b.sequence)
            .map((batteryAnalysis, index) => {
              const analysis = allAnalyses.find(a => a.id === batteryAnalysis.analysis_id);
              return (
                <Paper
                  key={batteryAnalysis.analysis_id}
                  variant="outlined"
                  sx={{ p: 2, mb: 1 }}
                >
                  <Box display="flex" alignItems="center" gap={2}>
                    <IconButton
                      size="small"
                      onClick={() => handleMoveUp(index)}
                      disabled={index === 0}
                    >
                      <DragIndicator />
                    </IconButton>
                    
                    <Box flex={1}>
                      <Typography variant="body2" fontWeight="medium">
                        {batteryAnalysis.analysis_name}
                      </Typography>
                      {batteryAnalysis.analysis_method && (
                        <Typography variant="caption" color="textSecondary">
                          {batteryAnalysis.analysis_method}
                        </Typography>
                      )}
                    </Box>

                    <TextField
                      size="small"
                      label="Sequence"
                      type="number"
                      value={batteryAnalysis.sequence}
                      onChange={(e) =>
                        handleSequenceChange(
                          batteryAnalysis.analysis_id,
                          parseInt(e.target.value) || 1
                        )
                      }
                      inputProps={{ min: 1 }}
                      sx={{ width: 100 }}
                    />

                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={batteryAnalysis.optional}
                          onChange={(e) =>
                            handleOptionalToggle(
                              batteryAnalysis.analysis_id,
                              e.target.checked
                            )
                          }
                        />
                      }
                      label="Optional"
                    />

                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleRemoveAnalysis(batteryAnalysis.analysis_id)}
                    >
                      <Delete />
                    </IconButton>
                  </Box>
                </Paper>
              );
            })}
        </Box>
      )}

      {availableAnalyses.length > 0 && (
        <Box mt={2}>
          <Typography variant="subtitle2" color="textSecondary" gutterBottom>
            Available Analyses
          </Typography>
          <FormControl fullWidth size="small">
            <InputLabel>Select Analysis to Add</InputLabel>
            <Select
              value=""
              onChange={(e) => {
                const analysisId = e.target.value;
                const analysis = allAnalyses.find(a => a.id === analysisId);
                if (analysis) {
                  const maxSequence = selectedAnalyses.length > 0
                    ? Math.max(...selectedAnalyses.map(a => a.sequence))
                    : 0;
                  
                  const newBatteryAnalysis: BatteryAnalysis = {
                    analysis_id: analysis.id,
                    analysis_name: analysis.name,
                    analysis_method: analysis.method,
                    sequence: maxSequence + 1,
                    optional: false,
                  };
                  
                  onChange([...selectedAnalyses, newBatteryAnalysis]);
                }
              }}
            >
              {availableAnalyses.map((analysis) => (
                <MenuItem key={analysis.id} value={analysis.id}>
                  {analysis.name}
                  {analysis.method && ` (${analysis.method})`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      )}
    </Box>
  );
};

export default AnalysisSelector;

