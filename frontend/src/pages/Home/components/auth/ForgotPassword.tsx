import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

interface ForgotPasswordProps {
  open: boolean;
  handleClose: () => void;
}

export default function ForgotPassword({ open, handleClose }: ForgotPasswordProps) {
  return (
    <Dialog open={open} onClose={handleClose} slotProps={{ paper: { sx: { backgroundImage: "none" } } }}>
      <DialogTitle>Password reset unavailable</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, width: "100%" }}>
        <DialogContentText>
          Email password reset is not enabled yet. Sign in with Google, or contact support if you
          need help accessing your account.
        </DialogContentText>
        <Alert severity="info" sx={{ mt: 1 }}>
          We will add self-service reset when the backend endpoint is ready.
        </Alert>
      </DialogContent>
      <DialogActions sx={{ pb: 3, px: 3 }}>
        <Button variant="contained" onClick={handleClose}>
          Got it
        </Button>
      </DialogActions>
    </Dialog>
  );
}
