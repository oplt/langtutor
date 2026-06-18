import type { Components } from '@mui/material/styles';
import type { Theme } from '@mui/material/styles';
import { tesla, teslaMotion } from '../themePrimitives';

export const surfacesCustomizations: Components<Theme> = {
  MuiAccordion: {
    defaultProps: { elevation: 0, disableGutters: true },
    styleOverrides: {
      root: ({ theme }) => ({
        padding: 4,
        overflow: 'clip',
        backgroundColor: (theme.vars || theme).palette.background.default,
        border: 'none',
        boxShadow: 'none',
        ':before': { backgroundColor: 'transparent' },
      }),
    },
  },
  MuiAccordionSummary: {
    styleOverrides: {
      root: ({ theme }) => ({
        border: 'none',
        borderRadius: (theme.vars || theme).shape.borderRadius,
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        '&:hover': { backgroundColor: tesla.lightAsh },
        ...theme.applyStyles('dark', {
          '&:hover': { backgroundColor: 'rgba(255,255,255,0.06)' },
        }),
      }),
    },
  },
  MuiAccordionDetails: {
    styleOverrides: {
      root: { paddingTop: 0, border: 'none' },
    },
  },
  MuiPaper: {
    defaultProps: { elevation: 0 },
    styleOverrides: {
      root: { backgroundImage: 'none', boxShadow: 'none' },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: ({ theme }) => ({
        padding: 16,
        gap: 16,
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        backgroundColor: (theme.vars || theme).palette.background.paper,
        borderRadius: (theme.vars || theme).shape.borderRadius,
        border: 'none',
        boxShadow: 'none',
        ...theme.applyStyles('dark', {
          backgroundColor: (theme.vars || theme).palette.background.paper,
        }),
        variants: [
          {
            props: { variant: 'outlined' },
            style: {
              border: 'none',
              boxShadow: 'none',
              backgroundColor: tesla.lightAsh,
              ...theme.applyStyles('dark', {
                backgroundColor: 'rgba(255,255,255,0.04)',
              }),
            },
          },
        ],
      }),
    },
  },
  MuiCardContent: {
    styleOverrides: {
      root: { padding: 0, '&:last-child': { paddingBottom: 0 } },
    },
  },
  MuiCardHeader: {
    styleOverrides: { root: { padding: 0 } },
  },
  MuiCardActions: {
    styleOverrides: { root: { padding: 0 } },
  },
};
