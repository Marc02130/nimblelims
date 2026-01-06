import React from 'react';
import {
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Box,
  Typography,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
}

interface CustomAttributeFieldProps {
  config: CustomAttributeConfig;
  value: any;
  onChange: (value: any) => void;
  onBlur?: () => void;
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  size?: 'small' | 'medium';
  label?: string;
}

const CustomAttributeField: React.FC<CustomAttributeFieldProps> = ({
  config,
  value,
  onChange,
  onBlur,
  error,
  helperText,
  fullWidth = true,
  size = 'medium',
  label,
}) => {
  const rules = config.validation_rules || {};
  const displayLabel = label || config.attr_name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

  const renderField = () => {
    switch (config.data_type) {
      case 'text':
        return (
          <TextField
            fullWidth={fullWidth}
            size={size}
            label={displayLabel}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            error={error}
            helperText={helperText || config.description}
            inputProps={{
              maxLength: rules.max_length,
              minLength: rules.min_length,
            }}
          />
        );

      case 'number':
        return (
          <TextField
            fullWidth={fullWidth}
            size={size}
            type="number"
            label={displayLabel}
            value={value ?? ''}
            onChange={(e) => {
              const numValue = e.target.value === '' ? null : parseFloat(e.target.value);
              onChange(numValue);
            }}
            onBlur={onBlur}
            error={error}
            helperText={helperText || config.description}
            inputProps={{
              min: rules.min,
              max: rules.max,
              step: 'any',
            }}
          />
        );

      case 'date':
        const minDate = rules.min_date ? new Date(rules.min_date) : undefined;
        const maxDate = rules.max_date ? new Date(rules.max_date) : undefined;
        return (
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DatePicker
              label={displayLabel}
              value={value ? new Date(value) : null}
              onChange={(date) => {
                onChange(date ? date.toISOString().split('T')[0] : null);
              }}
              onClose={() => {
                // Trigger validation when date picker closes
                if (onBlur) {
                  onBlur();
                }
              }}
              minDate={minDate}
              maxDate={maxDate}
              slotProps={{
                textField: {
                  fullWidth,
                  size,
                  error,
                  helperText: helperText || config.description,
                  onBlur: onBlur,
                },
              }}
            />
          </LocalizationProvider>
        );

      case 'boolean':
        return (
          <FormControlLabel
            control={
              <Checkbox
                checked={value === true || value === 'true'}
                onChange={(e) => onChange(e.target.checked)}
              />
            }
            label={
              <Box>
                <Typography variant="body2">{displayLabel}</Typography>
                {config.description && (
                  <Typography variant="caption" color="text.secondary">
                    {config.description}
                  </Typography>
                )}
              </Box>
            }
          />
        );

      case 'select':
        const options = rules.options || [];
        return (
          <FormControl fullWidth={fullWidth} size={size} error={error}>
            <InputLabel>{displayLabel}</InputLabel>
            <Select
              value={value || ''}
              onChange={(e) => onChange(e.target.value)}
              label={displayLabel}
            >
              <MenuItem value="">None</MenuItem>
              {options.map((option: string) => (
                <MenuItem key={option} value={option}>
                  {option}
                </MenuItem>
              ))}
            </Select>
            {helperText && (
              <Typography variant="caption" color={error ? 'error' : 'text.secondary'} sx={{ mt: 0.5, ml: 1.75 }}>
                {helperText}
              </Typography>
            )}
            {!helperText && config.description && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, ml: 1.75 }}>
                {config.description}
              </Typography>
            )}
          </FormControl>
        );

      default:
        return (
          <TextField
            fullWidth={fullWidth}
            size={size}
            label={displayLabel}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            error={error}
            helperText={helperText || config.description}
          />
        );
    }
  };

  return renderField();
};

export default CustomAttributeField;

