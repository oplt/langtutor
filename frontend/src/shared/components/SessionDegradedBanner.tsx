import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";

type SessionDegradedBannerProps = {
  onRetry: () => void;
};

export function SessionDegradedBanner({ onRetry }: SessionDegradedBannerProps) {
  return (
    <Alert
      severity="warning"
      sx={{ borderRadius: 0 }}
      action={
        <Button color="inherit" size="small" onClick={() => void onRetry()}>
          Retry
        </Button>
      }
    >
      We could not refresh your profile. Some dashboard details may be outdated until the
      connection recovers.
    </Alert>
  );
}
