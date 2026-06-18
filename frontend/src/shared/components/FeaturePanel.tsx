import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

import { PageLoading } from "./PageLoading";

type FeaturePanelProps = {
  title: string;
  description?: string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  children: ReactNode;
};

export function FeaturePanel({
  title,
  description,
  loading = false,
  error = null,
  onRetry,
  children,
}: FeaturePanelProps) {
  if (loading) {
    return <PageLoading label={`Loading ${title}…`} />;
  }

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h6">{title}</Typography>
        {description ? (
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        ) : null}
      </Box>
      {error ? (
        <Alert
          severity="error"
          action={
            onRetry ? (
              <Button color="inherit" size="small" onClick={onRetry}>
                Retry
              </Button>
            ) : undefined
          }
        >
          {error}
        </Alert>
      ) : null}
      {children}
    </Stack>
  );
}
