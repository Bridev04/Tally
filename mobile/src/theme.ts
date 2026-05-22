export const colors = {
  background: "#050807",
  backgroundAlt: "#070d0b",
  backgroundRaised: "#0a100e",
  surface: "#101816",
  surfaceAlt: "#121c19",
  surfaceRaised: "#16211e",
  elevated: "#18231f",
  elevatedAlt: "#1c2924",
  listSurface: "#141b18",
  primary: "#34d178",
  primaryStrong: "#28b765",
  primaryMuted: "#1f8f50",
  emeraldDeep: "#06452d",
  emeraldMid: "#0a5a3a",
  emerald: "#0f6b45",
  glow: "rgba(52, 209, 120, 0.18)",
  glowStrong: "rgba(52, 209, 120, 0.28)",
  text: "#f4f7f5",
  textSecondary: "#a5ada8",
  textMuted: "#737d78",
  border: "#26332e",
  borderStrong: "#2e3b36",
  amber: "#f2a93b",
  amberStrong: "#df982d",
  danger: "#ff5f57",
  nav: "#0b1110",
  navRaised: "#101816",
  navInactive: "#8a938e",
  white: "#ffffff",
  black: "#000000",
} as const;

export const lightColors = {
  background: "#f7f4ef",
  surface: "#ffffff",
  text: "#111816",
  textSecondary: "#5f6a63",
  border: "#d8d0c7",
  primary: "#256b5b",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  "2xl": 24,
  "3xl": 32,
  "4xl": 40,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  "2xl": 24,
  "3xl": 30,
  pill: 999,
} as const;

export const typography = {
  title: {
    fontSize: 30,
    fontWeight: "900" as const,
    lineHeight: 36,
  },
  headline: {
    fontSize: 24,
    fontWeight: "900" as const,
    lineHeight: 30,
  },
  section: {
    fontSize: 20,
    fontWeight: "900" as const,
    lineHeight: 26,
  },
  body: {
    fontSize: 15,
    fontWeight: "500" as const,
    lineHeight: 22,
  },
  label: {
    fontSize: 12,
    fontWeight: "800" as const,
    lineHeight: 16,
  },
} as const;

export const shadows = {
  glow: {
    shadowColor: colors.primary,
    shadowOpacity: 0.18,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 12 },
    elevation: 8,
  },
  card: {
    shadowColor: colors.black,
    shadowOpacity: 0.28,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
    elevation: 5,
  },
} as const;

export const gradients = {
  pulse: ["#063d29", "#1f5d46"],
  card: ["#101816", "#18231f"],
  list: ["#141b18", "#101412"],
} as const;

export const theme = {
  colors,
  gradients,
  lightColors,
  radius,
  shadows,
  spacing,
  typography,
} as const;

export type Theme = typeof theme;
