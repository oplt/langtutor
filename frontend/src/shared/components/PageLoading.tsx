import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

type PageLoadingProps = {
  label?: string;
};

const visuallyHiddenSx = {
  position: "absolute" as const,
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap" as const,
  border: 0,
};

export function PageLoading({ label = "Loading…" }: PageLoadingProps) {
  return (
    <Box
      role="status"
      aria-live="polite"
      aria-busy="true"
      sx={{
        minHeight: "40vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 1.5,
        position: "relative",
      }}
    >
      <Typography component="span" sx={visuallyHiddenSx}>
        {label}
      </Typography>
      <CircularProgress size={28} aria-hidden />
      <Typography variant="body2" color="text.secondary" aria-hidden>
        {label}
      </Typography>
    </Box>
  );
}
