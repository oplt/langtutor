import { createTheme, alpha } from '@mui/material/styles';
import type { Shadows } from '@mui/material/styles';
import type { PaletteMode } from '@mui/material/styles';

declare module '@mui/material/Paper' {
  interface PaperPropsVariantOverrides {
    highlighted: true;
  }
}
declare module '@mui/material/styles' {
  interface ColorRange {
    50: string;
    100: string;
    200: string;
    300: string;
    400: string;
    500: string;
    600: string;
    700: string;
    800: string;
    900: string;
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface PaletteColor extends ColorRange {}

  interface Palette {
    baseShadow: string;
  }

  interface Theme {
    tesla: typeof tesla;
    teslaMotion: typeof teslaMotion;
  }
  interface ThemeOptions {
    tesla?: typeof tesla;
    teslaMotion?: typeof teslaMotion;
  }
}

/** Tesla design tokens — see DESIGN.md */
export const tesla = {
  blue: '#3E6AE1',
  blueHover: '#345FD4',
  blueActive: '#2A53C7',
  white: '#FFFFFF',
  lightAsh: '#F4F4F4',
  carbon: '#171A20',
  graphite: '#393C41',
  pewter: '#5C5E62',
  silverFog: '#8E8E8E',
  cloudGray: '#EEEEEE',
  paleSilver: '#D0D1D2',
  frostGlass: 'rgba(255, 255, 255, 0.75)',
  overlay: 'rgba(128, 128, 128, 0.65)',
} as const;

export const teslaMotion = {
  standard: 'border-color 0.33s cubic-bezier(0.5, 0, 0, 0.75), background-color 0.33s cubic-bezier(0.5, 0, 0, 0.75), color 0.33s cubic-bezier(0.5, 0, 0, 0.75), box-shadow 0.25s cubic-bezier(0.5, 0, 0, 0.75)',
  link: 'box-shadow 0.33s cubic-bezier(0.5, 0, 0, 0.75), color 0.33s cubic-bezier(0.5, 0, 0, 0.75)',
} as const;

export const fontDisplay =
  '"Universal Sans Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif';
export const fontText =
  '"Universal Sans Text", -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif';

const defaultTheme = createTheme();

const noShadows: Shadows = Array(25).fill('none') as unknown as Shadows;

/** Electric blue scale — `brand` kept for existing customizations */
export const brand = {
  50: '#EBF0FB',
  100: '#D6E0F7',
  200: '#ADC1EF',
  300: '#84A2E7',
  400: tesla.blue,
  500: tesla.blue,
  600: tesla.blueHover,
  700: tesla.blueActive,
  800: '#1F3F9E',
  900: tesla.carbon,
};

/** Neutral scale mapped to Tesla grays */
export const gray = {
  50: tesla.white,
  100: tesla.lightAsh,
  200: tesla.cloudGray,
  300: tesla.paleSilver,
  400: tesla.silverFog,
  500: tesla.pewter,
  600: tesla.graphite,
  700: tesla.graphite,
  800: tesla.carbon,
  900: tesla.carbon,
};

export const green = {
  50: tesla.lightAsh,
  100: tesla.cloudGray,
  200: tesla.paleSilver,
  300: tesla.silverFog,
  400: tesla.pewter,
  500: tesla.graphite,
  600: tesla.graphite,
  700: tesla.carbon,
  800: tesla.carbon,
  900: tesla.carbon,
};

export const orange = {
  50: tesla.lightAsh,
  100: tesla.cloudGray,
  200: tesla.paleSilver,
  300: tesla.silverFog,
  400: tesla.pewter,
  500: tesla.graphite,
  600: tesla.graphite,
  700: tesla.carbon,
  800: tesla.carbon,
  900: tesla.carbon,
};

export const red = {
  50: tesla.lightAsh,
  100: tesla.cloudGray,
  200: tesla.paleSilver,
  300: tesla.silverFog,
  400: tesla.pewter,
  500: tesla.graphite,
  600: tesla.graphite,
  700: tesla.carbon,
  800: tesla.carbon,
  900: tesla.carbon,
};

export const typography = {
  fontFamily: fontText,
  h1: {
    fontFamily: fontDisplay,
    fontSize: defaultTheme.typography.pxToRem(40),
    fontWeight: 500,
    lineHeight: 1.2,
    letterSpacing: 'normal',
  },
  h2: {
    fontFamily: fontDisplay,
    fontSize: defaultTheme.typography.pxToRem(22),
    fontWeight: 400,
    lineHeight: 0.91,
    letterSpacing: 'normal',
  },
  h3: {
    fontFamily: fontText,
    fontSize: defaultTheme.typography.pxToRem(17),
    fontWeight: 500,
    lineHeight: 1.18,
    letterSpacing: 'normal',
  },
  h4: {
    fontFamily: fontText,
    fontSize: defaultTheme.typography.pxToRem(17),
    fontWeight: 500,
    lineHeight: 1.18,
    letterSpacing: 'normal',
  },
  h5: {
    fontFamily: fontText,
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 500,
    lineHeight: 1.2,
    letterSpacing: 'normal',
  },
  h6: {
    fontFamily: fontText,
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 500,
    lineHeight: 1.2,
    letterSpacing: 'normal',
  },
  subtitle1: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 500,
    lineHeight: 1.2,
  },
  subtitle2: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 500,
    lineHeight: 1.2,
  },
  body1: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 400,
    lineHeight: 1.43,
  },
  body2: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 400,
    lineHeight: 1.43,
  },
  button: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 500,
    lineHeight: 1.2,
    textTransform: 'none' as const,
    letterSpacing: 'normal',
  },
  caption: {
    fontSize: defaultTheme.typography.pxToRem(12),
    fontWeight: 400,
    lineHeight: 1.43,
  },
  overline: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 500,
    lineHeight: 1.2,
    letterSpacing: 'normal',
    textTransform: 'none' as const,
  },
};

export const shape = {
  borderRadius: 4,
};

export const shadows = noShadows;

export const getDesignTokens = (mode: PaletteMode) => ({
  tesla,
  teslaMotion,
  palette: {
    mode,
    primary: {
      light: brand[300],
      main: brand[500],
      dark: brand[700],
      contrastText: tesla.white,
    },
    info: {
      light: brand[200],
      main: brand[400],
      dark: brand[700],
      contrastText: tesla.white,
    },
    warning: {
      light: gray[200],
      main: gray[500],
      dark: gray[700],
    },
    error: {
      light: gray[200],
      main: gray[600],
      dark: gray[800],
    },
    success: {
      light: gray[200],
      main: gray[500],
      dark: gray[700],
    },
    grey: { ...gray },
    divider: mode === 'dark' ? alpha(tesla.paleSilver, 0.2) : tesla.cloudGray,
    background: {
      default: mode === 'dark' ? tesla.carbon : tesla.white,
      paper: mode === 'dark' ? '#1E2128' : tesla.white,
    },
    text: {
      primary: mode === 'dark' ? tesla.white : tesla.carbon,
      secondary: mode === 'dark' ? tesla.paleSilver : tesla.graphite,
      disabled: tesla.silverFog,
    },
    action: {
      hover: alpha(mode === 'dark' ? tesla.white : tesla.carbon, 0.04),
      selected: alpha(mode === 'dark' ? tesla.white : tesla.carbon, 0.08),
    },
  },
  typography,
  shape,
  shadows: noShadows,
});

export const colorSchemes = {
  light: {
    palette: {
      primary: {
        light: brand[300],
        main: brand[500],
        dark: brand[700],
        contrastText: tesla.white,
      },
      info: {
        light: brand[200],
        main: brand[400],
        dark: brand[700],
        contrastText: tesla.white,
      },
      warning: {
        light: gray[200],
        main: gray[500],
        dark: gray[700],
      },
      error: {
        light: gray[200],
        main: gray[600],
        dark: gray[800],
      },
      success: {
        light: gray[200],
        main: gray[500],
        dark: gray[700],
      },
      grey: { ...gray },
      divider: tesla.cloudGray,
      background: {
        default: tesla.white,
        paper: tesla.white,
      },
      text: {
        primary: tesla.carbon,
        secondary: tesla.graphite,
        disabled: tesla.silverFog,
      },
      action: {
        hover: alpha(tesla.carbon, 0.04),
        selected: alpha(tesla.carbon, 0.08),
      },
      baseShadow: 'none',
    },
  },
  dark: {
    palette: {
      primary: {
        light: brand[300],
        main: brand[500],
        dark: brand[700],
        contrastText: tesla.white,
      },
      info: {
        light: brand[200],
        main: brand[400],
        dark: brand[700],
        contrastText: tesla.white,
      },
      warning: {
        light: gray[700],
        main: gray[500],
        dark: gray[300],
      },
      error: {
        light: gray[700],
        main: gray[400],
        dark: gray[200],
      },
      success: {
        light: gray[700],
        main: gray[500],
        dark: gray[300],
      },
      grey: { ...gray },
      divider: alpha(tesla.paleSilver, 0.2),
      background: {
        default: tesla.carbon,
        paper: '#1E2128',
      },
      text: {
        primary: tesla.white,
        secondary: tesla.paleSilver,
        disabled: tesla.silverFog,
      },
      action: {
        hover: alpha(tesla.white, 0.06),
        selected: alpha(tesla.white, 0.1),
      },
      baseShadow: 'none',
    },
  },
};
