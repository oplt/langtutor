import { alpha } from '@mui/material/styles';
import type { Components } from '@mui/material/styles';
import type { Theme } from '@mui/material/styles';
import { svgIconClasses } from '@mui/material/SvgIcon';
import { typographyClasses } from '@mui/material/Typography';
import { buttonBaseClasses } from '@mui/material/ButtonBase';
import { chipClasses } from '@mui/material/Chip';
import { iconButtonClasses } from '@mui/material/IconButton';
import { tesla } from '../themePrimitives';

export const dataDisplayCustomizations: Components<Theme> = {
  MuiList: {
    styleOverrides: {
      root: {
        padding: '8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
      },
    },
  },
  MuiListItem: {
    styleOverrides: {
      root: ({ theme }) => ({
        [`& .${svgIconClasses.root}`]: {
          width: '1rem',
          height: '1rem',
          color: (theme.vars || theme).palette.text.secondary,
        },
        [`& .${typographyClasses.root}`]: { fontWeight: 500 },
        [`& .${buttonBaseClasses.root}`]: {
          display: 'flex',
          gap: 8,
          padding: '4px 16px',
          minHeight: 32,
          borderRadius: (theme.vars || theme).shape.borderRadius,
          '&:focus-visible': {
            outline: `3px solid ${alpha(tesla.blue, 0.45)}`,
            outlineOffset: '2px',
          },
          '&.Mui-selected': {
            backgroundColor: alpha(tesla.carbon, 0.06),
            [`& .${svgIconClasses.root}`]: {
              color: (theme.vars || theme).palette.text.primary,
            },
            '&:hover': { backgroundColor: alpha(tesla.carbon, 0.08) },
          },
        },
      }),
    },
  },
  MuiListItemText: {
    styleOverrides: {
      primary: ({ theme }) => ({
        fontSize: theme.typography.body2.fontSize,
        fontWeight: 500,
        lineHeight: theme.typography.body2.lineHeight,
      }),
      secondary: ({ theme }) => ({
        fontSize: theme.typography.caption.fontSize,
        lineHeight: theme.typography.caption.lineHeight,
        color: tesla.pewter,
      }),
    },
  },
  MuiListSubheader: {
    styleOverrides: {
      root: ({ theme }) => ({
        backgroundColor: 'transparent',
        padding: '4px 8px',
        fontSize: theme.typography.caption.fontSize,
        fontWeight: 500,
        color: tesla.pewter,
      }),
    },
  },
  MuiListItemIcon: {
    styleOverrides: { root: { minWidth: 0 } },
  },
  MuiChip: {
    defaultProps: { size: 'small' },
    styleOverrides: {
      root: ({ theme }) => ({
        border: 'none',
        borderRadius: (theme.vars || theme).shape.borderRadius,
        backgroundColor: tesla.lightAsh,
        [`& .${chipClasses.label}`]: {
          fontWeight: 500,
          color: tesla.graphite,
        },
        variants: [
          {
            props: { color: 'default' },
            style: {
              backgroundColor: tesla.lightAsh,
              [`& .${chipClasses.label}`]: { color: tesla.pewter },
            },
          },
          {
            props: { color: 'primary' },
            style: {
              backgroundColor: alpha(tesla.blue, 0.1),
              [`& .${chipClasses.label}`]: { color: tesla.blue },
            },
          },
          {
            props: { size: 'small' },
            style: {
              maxHeight: 24,
              [`& .${chipClasses.label}`]: { fontSize: theme.typography.caption.fontSize },
            },
          },
        ],
      }),
    },
  },
  MuiTablePagination: {
    styleOverrides: {
      actions: {
        display: 'flex',
        gap: 8,
        marginRight: 6,
        [`& .${iconButtonClasses.root}`]: { minWidth: 0, width: 36, height: 36 },
      },
    },
  },
  MuiIcon: {
    defaultProps: { fontSize: 'small' },
    styleOverrides: {
      root: {
        variants: [{ props: { fontSize: 'small' }, style: { fontSize: '1rem' } }],
      },
    },
  },
  MuiTypography: {
    styleOverrides: {
      gutterBottom: { marginBottom: 8 },
    },
  },
};
