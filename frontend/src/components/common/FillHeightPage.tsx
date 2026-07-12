import React from 'react';
import { Box, SxProps, Theme } from '@mui/material';

/**
 * Page shell that fills the MainLayout content area without scrolling the page.
 * Put title/search/actions in the header slot; put the table (or loading state)
 * as children so it expands and owns vertical scroll.
 */
export const FillHeightPage: React.FC<{
  header?: React.ReactNode;
  children: React.ReactNode;
  /** Extra sx on the root (rarely needed) */
  sx?: SxProps<Theme>;
}> = ({ header, children, sx }) => (
  <Box
    sx={{
      height: '100%',
      minHeight: 0,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      ...((sx as object) || {}),
    }}
  >
    {header != null && (
      <Box sx={{ flexShrink: 0, mb: 2 }}>{header}</Box>
    )}
    <Box
      sx={{
        flex: '1 1 0',
        minHeight: 0,
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {children}
    </Box>
  </Box>
);

/**
 * Wrapper that forces a MUI DataGrid (or similar) to fill remaining height.
 * Do not use DataGrid autoHeight with this — the grid must own scrolling.
 */
export const FillHeightTable: React.FC<{
  children: React.ReactNode;
  sx?: SxProps<Theme>;
}> = ({ children, sx }) => (
  <Box
    sx={{
      flex: '1 1 0',
      minHeight: 0,
      width: '100%',
      // DataGrid needs a definite height from its parent
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      ...((sx as object) || {}),
      '& .MuiDataGrid-root': {
        height: '100% !important',
        border: 0,
      },
    }}
  >
    {children}
  </Box>
);

export default FillHeightPage;
