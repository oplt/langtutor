import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";
import Header from "../components/Header";
import { useAuth } from "../../../context/AuthContext";

export default function AccountPage() {
  const { user } = useAuth();

  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h5" sx={{ mb: 0.5 }}>
                Account center
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Manage sign-in, privacy, and data controls for {user?.email || "your account"}.
              </Typography>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6">Security</Typography>
              <Divider sx={{ my: 1.5 }} />
              <Typography variant="body2" color="text.secondary">
                Password changes are not available in-app yet. If you signed in with Google, manage
                your credentials in your Google account. For email sign-in, password reset will be
                added in a future release.
              </Typography>
            </CardContent>
            <CardActions sx={{ px: 2, pb: 2 }}>
              <Button variant="text" component={RouterLink} to="/dashboard/settings">
                Review privacy settings
              </Button>
            </CardActions>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" color="error">
                Danger zone
              </Typography>
              <Divider sx={{ my: 1.5 }} />
              <Alert severity="warning" sx={{ mb: 2 }}>
                Sensitive actions are protected in Settings to prevent accidental account loss.
              </Alert>
              <Typography variant="body2" color="text.secondary">
                To request account deletion or clear retained data, use the controls on the Settings page.
              </Typography>
            </CardContent>
            <CardActions sx={{ px: 2, pb: 2 }}>
              <Button color="error" variant="outlined" component={RouterLink} to="/dashboard/settings">
                Go to settings
              </Button>
            </CardActions>
          </Card>
        </Stack>
      </Box>
    </>
  );
}
