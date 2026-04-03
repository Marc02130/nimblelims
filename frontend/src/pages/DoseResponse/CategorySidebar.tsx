import React from 'react';
import {
  Box,
  List,
  ListItemButton,
  ListItemText,
  Typography,
  Chip,
} from '@mui/material';

export const CATEGORIES = [
  'SIGMOID',
  'INACTIVE',
  'INVERSE',
  'PARTIAL_HIGH',
  'PARTIAL_LOW',
  'HOOK_EFFECT',
  'NOISY',
  'CANNOT_FIT',
] as const;

export type Category = typeof CATEGORIES[number];

export const CATEGORY_LABELS: Record<Category, string> = {
  SIGMOID: 'Sigmoid',
  INACTIVE: 'Inactive',
  INVERSE: 'Inverse Agonist',
  PARTIAL_HIGH: 'Partial High',
  PARTIAL_LOW: 'Partial Low',
  HOOK_EFFECT: 'Hook Effect',
  NOISY: 'Noisy',
  CANNOT_FIT: 'Cannot Fit',
};

const CATEGORY_CHIP_COLORS: Record<Category, string> = {
  SIGMOID: '#2e7d32',
  INACTIVE: '#757575',
  INVERSE: '#ed6c02',
  PARTIAL_HIGH: '#0288d1',
  PARTIAL_LOW: '#0288d1',
  HOOK_EFFECT: '#f57c00',
  NOISY: '#7b1fa2',
  CANNOT_FIT: '#d32f2f',
};

interface Props {
  byCategoryCount: Record<string, number>;
  selected: Category;
  onSelect: (cat: Category) => void;
}

const CategorySidebar: React.FC<Props> = ({ byCategoryCount, selected, onSelect }) => {
  return (
    <Box
      sx={{
        width: 200,
        flexShrink: 0,
        borderRight: 1,
        borderColor: 'divider',
        height: '100%',
        overflowY: 'auto',
      }}
    >
      <Typography variant="subtitle2" sx={{ px: 2, pt: 2, pb: 1 }} color="text.secondary">
        Categories
      </Typography>
      <List dense disablePadding>
        {CATEGORIES.map((cat) => {
          const count = byCategoryCount[cat] ?? 0;
          return (
            <ListItemButton
              key={cat}
              selected={selected === cat}
              disabled={count === 0}
              onClick={() => onSelect(cat)}
              sx={{ px: 2, py: 1 }}
            >
              <ListItemText
                primary={CATEGORY_LABELS[cat]}
                primaryTypographyProps={{ variant: 'body2', noWrap: true }}
              />
              <Box
                sx={{
                  minWidth: 24,
                  height: 20,
                  borderRadius: 1,
                  px: 0.75,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: count > 0 ? CATEGORY_CHIP_COLORS[cat] : 'action.disabledBackground',
                  color: count > 0 ? '#fff' : 'text.disabled',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                }}
              >
                {count}
              </Box>
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );
};

export default CategorySidebar;
