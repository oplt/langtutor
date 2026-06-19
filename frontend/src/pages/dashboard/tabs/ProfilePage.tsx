import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import { useEffect, useState } from "react";
import Header from "../components/Header";
import { useAuth } from "../../../context/AuthContext";
import { updateProfile } from "../../../modules/auth/api/authApi";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [loadingProfile, setLoadingProfile] = useState(false);
  const displayName = user?.full_name?.trim() || "Language learner";
  const displayEmail = user?.email || "user@email.com";
  const initials = displayName.charAt(0).toUpperCase();
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    full_name: user?.full_name ?? "",
  });

  useEffect(() => {
    setForm({
      full_name: user?.full_name ?? "",
    });
  }, [user]);

  useEffect(() => {
    if (user) return;
    let active = true;
    setLoadingProfile(true);
    refreshUser()
      .catch(() => {
        if (!active) return;
        setError("Could not load profile details.");
      })
      .finally(() => {
        if (!active) return;
        setLoadingProfile(false);
      });
    return () => {
      active = false;
    };
  }, [user, refreshUser]);

  const saveProfile = async () => {
    const trimmed = form.full_name.trim();
    if (trimmed.length < 2) {
      setError("Full name must be at least 2 characters.");
      setNotice(null);
      return;
    }
    setSaving(true);
    setNotice(null);
    setError(null);
    try {
      await updateProfile(trimmed);
      await refreshUser();
      setForm({ full_name: trimmed });
      setNotice("Profile updated.");
    } catch {
      setError("Could not save profile changes.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
        <Stack spacing={2}>
          {loadingProfile && <Alert severity="info">Loading profile details...</Alert>}
          {notice && <Alert severity="success">{notice}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}
          <Card variant="outlined">
            <CardContent>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={2}
                alignItems={{ xs: "flex-start", sm: "center" }}
              >
                <Avatar sx={{ width: 64, height: 64 }}>{initials}</Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h5">
                    {displayName}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {displayEmail}
                  </Typography>
                </Box>
                <Chip color="success" label="Profile active" />
              </Stack>
            </CardContent>
          </Card>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    Personal details
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Stack spacing={1.5}>
                    <TextField
                      label="Full name"
                      size="small"
                      value={form.full_name}
                      error={form.full_name.trim().length > 0 && form.full_name.trim().length < 2}
                      helperText={
                        form.full_name.trim().length > 0 && form.full_name.trim().length < 2
                          ? "Use at least 2 characters."
                          : undefined
                      }
                      onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))}
                    />
                    <TextField label="Email" size="small" value={displayEmail} disabled />
                    <Button
                      variant="contained"
                      onClick={saveProfile}
                      disabled={saving || form.full_name.trim().length < 2}
                    >
                      {saving ? "Saving..." : "Save profile"}
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Stack>
      </Box>
    </>
  );
}
