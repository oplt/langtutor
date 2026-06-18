import * as React from 'react';
import { alpha } from '@mui/material/styles';
import type { Components } from '@mui/material/styles';
import type { Theme } from '@mui/material/styles';
import type { SvgIconProps } from '@mui/material/SvgIcon';
import { buttonBaseClasses } from '@mui/material/ButtonBase';
import { dividerClasses } from '@mui/material/Divider';
import { menuItemClasses } from '@mui/material/MenuItem';
import { selectClasses } from '@mui/material/Select';
import { tabClasses } from '@mui/material/Tab';
import UnfoldMoreRoundedIcon from '@mui/icons-material/UnfoldMoreRounded';
import { brand, tesla, teslaMotion } from '../themePrimitives';

export const navigationCustomizations: Components<Theme> = {
  MuiAppBar: {
    styleOverrides: {
      root: {
        boxShadow: 'none',
        backgroundImage: 'none',
      },
    },
  },
  MuiMenuItem: {
    styleOverrides: {
      root: ({ theme }) => ({
        borderRadius: (theme.vars || theme).shape.borderRadius,
        padding: '6px 8px',
        fontSize: '0.875rem',
        fontWeight: 500,
        [`&.${menuItemClasses.focusVisible}`]: { backgroundColor: 'transparent' },
        [`&.${menuItemClasses.selected}`]: {
          [`&.${menuItemClasses.focusVisible}`]: {
            backgroundColor: alpha(theme.palette.action.selected, 0.3),
          },
        },
      }),
    },
  },
  MuiMenu: {
    styleOverrides: {
      list: {
        gap: '0px',
        [`&.${dividerClasses.root}`]: { margin: '0 -8px' },
      },
      paper: ({ theme }) => ({
        marginTop: '4px',
        borderRadius: (theme.vars || theme).shape.borderRadius,
        border: 'none',
        backgroundImage: 'none',
        background: tesla.white,
        boxShadow: 'none',
        [`& .${buttonBaseClasses.root}`]: {
          '&.Mui-selected': { backgroundColor: alpha(theme.palette.action.selected, 0.3) },
        },
        ...theme.applyStyles('dark', { background: tesla.carbon }),
      }),
    },
  },
  MuiSelect: {
    defaultProps: {
      IconComponent: React.forwardRef<SVGSVGElement, SvgIconProps>((props, ref) => (
        <UnfoldMoreRoundedIcon fontSize="small" {...props} ref={ref} />
      )),
    },
    styleOverrides: {
      root: ({ theme }) => ({
        borderRadius: (theme.vars || theme).shape.borderRadius,
        border: `1px solid ${tesla.paleSilver}`,
        backgroundColor: (theme.vars || theme).palette.background.paper,
        boxShadow: 'none',
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        '&:hover': {
          borderColor: tesla.silverFog,
          backgroundColor: (theme.vars || theme).palette.background.paper,
        },
        [`&.${selectClasses.focused}`]: {
          outlineOffset: 0,
          borderColor: tesla.blue,
        },
        '&:before, &:after': { display: 'none' },
        ...theme.applyStyles('dark', {
          borderColor: alpha(tesla.paleSilver, 0.35),
        }),
      }),
      select: { display: 'flex', alignItems: 'center' },
    },
  },
  MuiLink: {
    defaultProps: { underline: 'none' },
    styleOverrides: {
      root: ({ theme }) => ({
        color: tesla.pewter,
        fontWeight: 400,
        fontSize: '0.875rem',
        textDecoration: 'none',
        transition: theme.teslaMotion?.link ?? teslaMotion.link,
        '&:hover': {
          color: tesla.graphite,
          textDecoration: 'underline',
        },
        '&:focus-visible': {
          outline: `3px solid ${alpha(brand[500], 0.45)}`,
          outlineOffset: '4px',
          borderRadius: '2px',
        },
        ...theme.applyStyles('dark', {
          color: tesla.paleSilver,
          '&:hover': { color: tesla.white },
        }),
      }),
    },
  },
  MuiDrawer: {
    styleOverrides: {
      paper: ({ theme }) => ({
        backgroundColor: (theme.vars || theme).palette.background.default,
        borderRight: `1px solid ${tesla.cloudGray}`,
        boxShadow: 'none',
        ...theme.applyStyles('dark', {
          borderRight: `1px solid ${alpha(tesla.paleSilver, 0.15)}`,
        }),
      }),
    },
  },
  MuiPaginationItem: {
    styleOverrides: {
      root: ({ theme }) => ({
        borderRadius: (theme.vars || theme).shape.borderRadius,
        '&.Mui-selected': {
          color: tesla.white,
          backgroundColor: tesla.blue,
        },
      }),
    },
  },
  MuiTabs: {
    styleOverrides: {
      root: { minHeight: 'fit-content' },
      indicator: { backgroundColor: tesla.blue, height: 2 },
    },
  },
  MuiTab: {
    styleOverrides: {
      root: ({ theme }) => ({
        padding: '6px 16px',
        marginBottom: '8px',
        textTransform: 'none',
        minWidth: 'fit-content',
        minHeight: '2rem',
        fontSize: '0.875rem',
        fontWeight: 500,
        color: tesla.pewter,
        borderRadius: (theme.vars || theme).shape.borderRadius,
        border: 'none',
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        ':hover': {
          color: tesla.carbon,
          backgroundColor: tesla.lightAsh,
        },
        [`&.${tabClasses.selected}`]: { color: tesla.carbon },
        ...theme.applyStyles('dark', {
          ':hover': { color: tesla.white, backgroundColor: alpha(tesla.white, 0.06) },
          [`&.${tabClasses.selected}`]: { color: tesla.white },
        }),
      }),
    },
  },
  MuiStepConnector: {
    styleOverrides: {
      line: ({ theme }) => ({
        borderTop: `1px solid ${(theme.vars || theme).palette.divider}`,
        flex: 1,
      }),
    },
  },
  MuiStepIcon: {
    styleOverrides: {
      root: () => ({
        color: 'transparent',
        border: `1px solid ${tesla.paleSilver}`,
        width: 12,
        height: 12,
        borderRadius: '50%',
        '& text': { display: 'none' },
        '&.Mui-active': { border: 'none', color: tesla.blue },
        '&.Mui-completed': { border: 'none', color: tesla.blue },
      }),
    },
  },
  MuiStepLabel: {
    styleOverrides: {
      label: () => ({
        '&.Mui-completed': { opacity: 0.6 },
      }),
    },
  },
  MuiBreadcrumbs: {
    styleOverrides: {
      li: { fontSize: '0.875rem', color: tesla.pewter },
    },
  },
};
