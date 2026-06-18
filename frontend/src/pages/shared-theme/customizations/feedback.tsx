import { alpha } from '@mui/material/styles';
import type { Components } from '@mui/material/styles';
import type { Theme } from '@mui/material/styles';
import { tesla } from '../themePrimitives';

export const feedbackCustomizations: Components<Theme> = {
  MuiAlert: {
    styleOverrides: {
      root: ({ theme }) => ({
        borderRadius: (theme.vars || theme).shape.borderRadius,
        backgroundColor: tesla.lightAsh,
        color: tesla.graphite,
        border: 'none',
        boxShadow: 'none',
        '& .MuiAlert-icon': { color: tesla.pewter },
        ...theme.applyStyles('dark', {
          backgroundColor: alpha(tesla.white, 0.06),
          color: tesla.white,
        }),
      }),
    },
  },
  MuiDialog: {
    styleOverrides: {
      root: ({ theme }) => ({
        '& .MuiBackdrop-root': { backgroundColor: tesla.overlay },
        '& .MuiDialog-paper': {
          borderRadius: (theme.vars || theme).shape.borderRadius,
          border: 'none',
          boxShadow: 'none',
        },
      }),
    },
  },
  MuiLinearProgress: {
    styleOverrides: {
      root: ({ theme }) => ({
        height: 4,
        borderRadius: 4,
        backgroundColor: tesla.cloudGray,
        '& .MuiLinearProgress-bar': { backgroundColor: tesla.blue },
        ...theme.applyStyles('dark', { backgroundColor: alpha(tesla.white, 0.12) }),
      }),
    },
  },
  MuiCircularProgress: {
    styleOverrides: {
      root: { color: tesla.blue },
    },
  },
};
