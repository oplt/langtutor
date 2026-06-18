import { Box, Stack, Typography } from "@mui/material";
import { tesla } from "../../../shared-theme/themePrimitives";

type Highlight = {
  value: string;
  label: string;
};

type AuthMarketingPanelProps = {
  appName: string;
  eyebrow: string;
  title: string;
  description: string;
  highlights?: Highlight[];
  points?: string[];
};

export function AuthMarketingPanel({
  appName,
  eyebrow,
  title,
  description,
  highlights = [],
  points = [],
}: AuthMarketingPanelProps) {
  return (
    <Stack justifyContent="space-between" spacing={4} sx={{ height: "100%" }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="overline" sx={{ color: "text.secondary", display: "block", mb: 1 }}>
            {eyebrow}
          </Typography>
          <Typography variant="h1" sx={{ mb: 1.25, fontSize: { xs: "1.75rem", md: "2.5rem" } }}>
            {title}
          </Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 620 }}>
            {description}
          </Typography>
        </Box>

        {highlights.length > 0 && (
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" },
            }}
          >
            {highlights.map((item) => (
              <Box
                key={item.label}
                sx={{
                  p: 2,
                  borderRadius: 3,
                  bgcolor: tesla.white,
                }}
              >
                <Typography variant="h3">{item.value}</Typography>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  {item.label}
                </Typography>
              </Box>
            ))}
          </Box>
        )}
      </Stack>

      <Stack spacing={1.25}>
        <Typography variant="subtitle2" color="text.primary">
          {appName}
        </Typography>
        {points.map((point) => (
          <Box
            key={point}
            sx={{
              p: 1.5,
              borderRadius: 1,
              bgcolor: tesla.white,
            }}
          >
            <Typography color="text.secondary">{point}</Typography>
          </Box>
        ))}
      </Stack>
    </Stack>
  );
}
