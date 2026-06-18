import { Box, Paper } from "@mui/material";
import { tesla } from "../../../shared-theme/themePrimitives";

type AuthShellProps = {
  sideContent: React.ReactNode;
  children: React.ReactNode;
};

export function AuthShell({ sideContent, children }: AuthShellProps) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.08fr) minmax(420px, 0.92fr)" },
        gap: { xs: 2.5, lg: 3 },
        alignItems: "stretch",
      }}
    >
      <Paper
        sx={{
          p: { xs: 3, md: 4.5 },
          borderRadius: 3,
          overflow: "hidden",
          bgcolor: tesla.lightAsh,
          boxShadow: "none",
          border: "none",
        }}
      >
        {sideContent}
      </Paper>
      <Paper
        sx={{
          p: { xs: 3, md: 4 },
          borderRadius: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "none",
          border: "none",
        }}
      >
        <Box sx={{ width: "100%", maxWidth: 440 }}>{children}</Box>
      </Paper>
    </Box>
  );
}
