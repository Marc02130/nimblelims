/**
 * Shared chip filter row for list pages (idea: list-page-search).
 * Single-select chips; empty value = "All".
 */
import React from 'react';
import { Box, Chip, Typography } from '@mui/material';

export type ListFilterChipOption = {
  value: string;
  label: string;
};

export interface ListFilterChipsProps {
  /** Optional group label shown before chips */
  label?: string;
  options: ListFilterChipOption[];
  /** Selected value; '' means All / none of the specific chips */
  value: string;
  onChange: (value: string) => void;
  /** Include an "All" chip that clears the filter (default true) */
  showAll?: boolean;
  allLabel?: string;
  size?: 'small' | 'medium';
  disabled?: boolean;
}

const ListFilterChips: React.FC<ListFilterChipsProps> = ({
  label,
  options,
  value,
  onChange,
  showAll = true,
  allLabel = 'All',
  size = 'small',
  disabled = false,
}) => {
  return (
    <Box
      display="flex"
      flexWrap="wrap"
      alignItems="center"
      gap={0.75}
      sx={{ mb: 1.5 }}
      role="group"
      aria-label={label || 'Filters'}
    >
      {label && (
        <Typography variant="body2" color="text.secondary" sx={{ mr: 0.5 }}>
          {label}
        </Typography>
      )}
      {showAll && (
        <Chip
          size={size}
          label={allLabel}
          color={!value ? 'primary' : 'default'}
          variant={!value ? 'filled' : 'outlined'}
          onClick={() => !disabled && onChange('')}
          disabled={disabled}
          aria-pressed={!value}
        />
      )}
      {options.map((opt) => {
        const selected = value === opt.value;
        return (
          <Chip
            key={opt.value || opt.label}
            size={size}
            label={opt.label}
            color={selected ? 'primary' : 'default'}
            variant={selected ? 'filled' : 'outlined'}
            onClick={() => !disabled && onChange(selected ? '' : opt.value)}
            disabled={disabled}
            aria-pressed={selected}
          />
        );
      })}
    </Box>
  );
};

export default ListFilterChips;
