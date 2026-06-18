import { alpha } from '@mui/material/styles';
import type { Components } from '@mui/material/styles';
import type { Theme } from '@mui/material/styles';
import { outlinedInputClasses } from '@mui/material/OutlinedInput';
import { svgIconClasses } from '@mui/material/SvgIcon';
import { toggleButtonGroupClasses } from '@mui/material/ToggleButtonGroup';
import { toggleButtonClasses } from '@mui/material/ToggleButton';
import CheckBoxOutlineBlankRoundedIcon from '@mui/icons-material/CheckBoxOutlineBlankRounded';
import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import RemoveRoundedIcon from '@mui/icons-material/RemoveRounded';
import { brand, tesla, teslaMotion } from '../themePrimitives';

export const inputsCustomizations: Components<Theme> = {
  MuiButtonBase: {
    defaultProps: {
      disableTouchRipple: true,
      disableRipple: true,
    },
    styleOverrides: {
      root: ({ theme }) => ({
        boxSizing: 'border-box',
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        '&:focus-visible': {
          outline: `3px solid ${alpha(brand[500], 0.45)}`,
          outlineOffset: '2px',
        },
      }),
    },
  },
  MuiButton: {
    styleOverrides: {
      root: ({ theme }) => ({
        boxShadow: 'none',
        borderRadius: (theme.vars || theme).shape.borderRadius,
        textTransform: 'none',
        fontWeight: 500,
        letterSpacing: 'normal',
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        variants: [
          {
            props: { size: 'small' },
            style: { minHeight: '2rem', padding: '4px 12px' },
          },
          {
            props: { size: 'medium' },
            style: { minHeight: '2.5rem', padding: '4px 16px' },
          },
          {
            props: { color: 'primary', variant: 'contained' },
            style: {
              color: tesla.white,
              backgroundColor: tesla.blue,
              border: '3px solid transparent',
              '&:hover': { backgroundColor: tesla.blueHover, boxShadow: 'none' },
              '&:active': { backgroundColor: tesla.blueActive },
            },
          },
          {
            props: { color: 'secondary', variant: 'contained' },
            style: {
              color: tesla.graphite,
              backgroundColor: tesla.white,
              border: '3px solid transparent',
              '&:hover': { backgroundColor: tesla.lightAsh, boxShadow: 'none' },
            },
          },
          {
            props: { variant: 'outlined' },
            style: {
              color: tesla.graphite,
              border: `1px solid ${tesla.paleSilver}`,
              backgroundColor: tesla.white,
              '&:hover': {
                backgroundColor: tesla.lightAsh,
                borderColor: tesla.paleSilver,
              },
              ...theme.applyStyles('dark', {
                backgroundColor: 'transparent',
                borderColor: alpha(tesla.paleSilver, 0.35),
                color: tesla.white,
                '&:hover': { backgroundColor: alpha(tesla.white, 0.06) },
              }),
            },
          },
          {
            props: { variant: 'text' },
            style: {
              color: tesla.pewter,
              '&:hover': { backgroundColor: alpha(tesla.carbon, 0.04) },
              ...theme.applyStyles('dark', {
                color: tesla.paleSilver,
                '&:hover': { backgroundColor: alpha(tesla.white, 0.06) },
              }),
            },
          },
        ],
      }),
    },
  },
  MuiIconButton: {
    styleOverrides: {
      root: ({ theme }) => ({
        boxShadow: 'none',
        borderRadius: (theme.vars || theme).shape.borderRadius,
        border: 'none',
        backgroundColor: 'transparent',
        color: tesla.carbon,
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        '&:hover': { backgroundColor: alpha(tesla.carbon, 0.04) },
        ...theme.applyStyles('dark', {
          color: tesla.white,
          '&:hover': { backgroundColor: alpha(tesla.white, 0.06) },
        }),
        variants: [
          {
            props: { size: 'small' },
            style: {
              width: '2rem',
              height: '2rem',
              [`& .${svgIconClasses.root}`]: { fontSize: '1rem' },
            },
          },
          {
            props: { size: 'medium' },
            style: { width: '2.5rem', height: '2.5rem' },
          },
        ],
      }),
    },
  },
  MuiToggleButtonGroup: {
    styleOverrides: {
      root: ({ theme }) => ({
        borderRadius: (theme.vars || theme).shape.borderRadius,
        boxShadow: 'none',
        backgroundColor: tesla.lightAsh,
        [`& .${toggleButtonGroupClasses.selected}`]: {
          color: tesla.carbon,
          backgroundColor: tesla.white,
        },
        ...theme.applyStyles('dark', {
          backgroundColor: alpha(tesla.white, 0.08),
          [`& .${toggleButtonGroupClasses.selected}`]: {
            color: tesla.white,
            backgroundColor: alpha(tesla.white, 0.12),
          },
        }),
      }),
    },
  },
  MuiToggleButton: {
    styleOverrides: {
      root: ({ theme }) => ({
        padding: '8px 16px',
        textTransform: 'none',
        borderRadius: (theme.vars || theme).shape.borderRadius,
        fontWeight: 500,
        border: 'none',
        color: tesla.pewter,
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        [`&.${toggleButtonClasses.selected}`]: {
          color: tesla.carbon,
        },
        ...theme.applyStyles('dark', {
          color: tesla.paleSilver,
          [`&.${toggleButtonClasses.selected}`]: { color: tesla.white },
        }),
      }),
    },
  },
  MuiCheckbox: {
    defaultProps: {
      disableRipple: true,
      icon: <CheckBoxOutlineBlankRoundedIcon sx={{ color: 'transparent' }} />,
      checkedIcon: <CheckRoundedIcon sx={{ height: 14, width: 14 }} />,
      indeterminateIcon: <RemoveRoundedIcon sx={{ height: 14, width: 14 }} />,
    },
    styleOverrides: {
      root: ({ theme }) => ({
        margin: 8,
        height: 16,
        width: 16,
        borderRadius: 4,
        border: `1px solid ${tesla.paleSilver}`,
        backgroundColor: tesla.white,
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        '&:hover': { borderColor: tesla.silverFog },
        '&.Mui-checked': {
          color: tesla.white,
          backgroundColor: tesla.blue,
          borderColor: tesla.blue,
          '&:hover': { backgroundColor: tesla.blueHover },
        },
        ...theme.applyStyles('dark', {
          backgroundColor: 'transparent',
          borderColor: alpha(tesla.paleSilver, 0.4),
        }),
      }),
    },
  },
  MuiInputBase: {
    styleOverrides: {
      root: { border: 'none' },
      input: {
        '&::placeholder': { opacity: 1, color: tesla.silverFog },
      },
    },
  },
  MuiOutlinedInput: {
    styleOverrides: {
      input: { padding: 0 },
      root: ({ theme }) => ({
        padding: '8px 12px',
        color: (theme.vars || theme).palette.text.primary,
        borderRadius: (theme.vars || theme).shape.borderRadius,
        border: `1px solid ${tesla.paleSilver}`,
        backgroundColor: 'transparent',
        transition: theme.teslaMotion?.standard ?? teslaMotion.standard,
        '&:hover': { borderColor: tesla.silverFog },
        [`&.${outlinedInputClasses.focused}`]: {
          outline: `3px solid ${alpha(brand[500], 0.35)}`,
          borderColor: tesla.blue,
        },
        variants: [
          { props: { size: 'small' }, style: { height: '2.25rem' } },
          { props: { size: 'medium' }, style: { height: '2.5rem' } },
        ],
      }),
      notchedOutline: { border: 'none' },
    },
  },
  MuiInputAdornment: {
    styleOverrides: {
      root: { color: tesla.silverFog },
    },
  },
  MuiFormLabel: {
    styleOverrides: {
      root: ({ theme }) => ({
        typography: theme.typography.caption,
        marginBottom: 8,
        color: tesla.graphite,
      }),
    },
  },
};
