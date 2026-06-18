import * as React from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Collapse,
  Divider,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  type TextFieldProps,
  Typography,
} from "@mui/material";
import { Visibility, VisibilityOff } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import { login, signup } from "../../../modules/auth/api/authApi";
import { ApiError } from "../../../shared/api/httpClient";
import { API_BASE } from "../../../config";
import { shouldRememberSession } from "../../../auth";
import { AuthMarketingPanel } from "./auth/AuthMarketingPanel";
import { AuthShell } from "./auth/AuthShell";
import ForgotPassword from "./auth/ForgotPassword";
import { GoogleIcon } from "./auth/GoogleIcon";

type Mode = "signIn" | "signUp";

function PasswordField(props: TextFieldProps) {
  const [showPassword, setShowPassword] = React.useState(false);

  return (
    <TextField
      {...props}
      type={showPassword ? "text" : "password"}
      InputProps={{
        endAdornment: (
          <InputAdornment position="end">
            <IconButton
              edge="end"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword((value) => !value)}
              onMouseDown={(event) => event.preventDefault()}
            >
              {showPassword ? <VisibilityOff /> : <Visibility />}
            </IconButton>
          </InputAdornment>
        ),
      }}
    />
  );
}

function SignInForm({
  onForgotOpen,
  rememberMe,
  onRememberMeChange,
}: {
  onForgotOpen: () => void;
  rememberMe: boolean;
  onRememberMeChange: (value: boolean) => void;
}) {
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const [emailError, setEmailError] = React.useState(false);
  const [emailErrorMessage, setEmailErrorMessage] = React.useState("");
  const [passwordError, setPasswordError] = React.useState(false);
  const [passwordErrorMessage, setPasswordErrorMessage] = React.useState("");
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const validateInputs = (email: string, password: string) => {
    let isValid = true;

    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      setEmailError(true);
      setEmailErrorMessage("Please enter a valid email address.");
      isValid = false;
    } else {
      setEmailError(false);
      setEmailErrorMessage("");
    }

    if (!password || password.length < 8) {
      setPasswordError(true);
      setPasswordErrorMessage("Password must be at least 8 characters long.");
      isValid = false;
    } else {
      setPasswordError(false);
      setPasswordErrorMessage("");
    }

    return isValid;
  };

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const data = new FormData(event.currentTarget);
    const email = String(data.get("email"));
    const password = String(data.get("password"));

    if (!validateInputs(email, password)) return;

    setIsSubmitting(true);
    try {
      const json = await login(email, password);
      loginWithToken(json.access_token, rememberMe);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setPasswordError(true);
        setPasswordErrorMessage(err.message);
      } else {
        setSubmitError("Unable to reach the server. Check that the backend is running.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Stack spacing={2}>
      {submitError && <Alert severity="error">{submitError}</Alert>}
      <Box component="form" onSubmit={onSubmit}>
        <Stack spacing={2}>
          <TextField
            label="Email"
            type="email"
            name="email"
            autoComplete="email"
            error={emailError}
            helperText={emailErrorMessage}
            fullWidth
          />
          <PasswordField
            label="Password"
            name="password"
            autoComplete="current-password"
            error={passwordError}
            helperText={passwordErrorMessage}
            fullWidth
          />
          <FormControlLabel
            control={
              <Checkbox
                name="remember"
                checked={rememberMe}
                onChange={(e) => onRememberMeChange(e.target.checked)}
                color="primary"
              />
            }
            label="Remember me"
          />
          <Button type="submit" variant="contained" size="large" disabled={isSubmitting} fullWidth>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </Button>
          <Button variant="text" onClick={onForgotOpen} sx={{ alignSelf: "flex-start", px: 0 }}>
            Forgot password?
          </Button>
        </Stack>
      </Box>
      <Divider>or</Divider>
      <Button
        fullWidth
        variant="outlined"
        onClick={() => {
          window.location.href = `${API_BASE}/auth/google/login?mode=signin`;
        }}
        startIcon={<GoogleIcon />}
      >
        Sign in with Google
      </Button>
    </Stack>
  );
}

function SignUpForm({ onSuccess }: { onSuccess: (email: string) => void }) {
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const [emailError, setEmailError] = React.useState(false);
  const [emailErrorMessage, setEmailErrorMessage] = React.useState("");
  const [passwordError, setPasswordError] = React.useState(false);
  const [passwordErrorMessage, setPasswordErrorMessage] = React.useState("");
  const [confirmPasswordError, setConfirmPasswordError] = React.useState(false);
  const [confirmPasswordErrorMessage, setConfirmPasswordErrorMessage] = React.useState("");
  const [nameError, setNameError] = React.useState(false);
  const [nameErrorMessage, setNameErrorMessage] = React.useState("");
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const validateInputs = (name: string, email: string, password: string, confirmPassword: string) => {
    let isValid = true;

    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      setEmailError(true);
      setEmailErrorMessage("Please enter a valid email address.");
      isValid = false;
    } else {
      setEmailError(false);
      setEmailErrorMessage("");
    }

    if (!password || password.length < 8) {
      setPasswordError(true);
      setPasswordErrorMessage("Password must be at least 8 characters long.");
      isValid = false;
    } else {
      setPasswordError(false);
      setPasswordErrorMessage("");
    }

    if (!confirmPassword) {
      setConfirmPasswordError(true);
      setConfirmPasswordErrorMessage("Please confirm your password.");
      isValid = false;
    } else if (confirmPassword !== password) {
      setConfirmPasswordError(true);
      setConfirmPasswordErrorMessage("Passwords do not match.");
      isValid = false;
    } else {
      setConfirmPasswordError(false);
      setConfirmPasswordErrorMessage("");
    }

    if (!name || name.length < 1) {
      setNameError(true);
      setNameErrorMessage("Name is required.");
      isValid = false;
    } else {
      setNameError(false);
      setNameErrorMessage("");
    }

    return isValid;
  };

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const data = new FormData(event.currentTarget);
    const full_name = String(data.get("full_name") ?? "").trim();
    const email = String(data.get("email"));
    const password = String(data.get("password"));
    const confirmPassword = String(data.get("confirm_password"));

    if (!validateInputs(full_name, email, password, confirmPassword)) return;

    setIsSubmitting(true);
    try {
      const json = await signup(full_name, email, password);
      loginWithToken(json.access_token);
      onSuccess(email);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setEmailError(true);
        setEmailErrorMessage(err.message);
      } else {
        setSubmitError("Unable to reach the server. Check that the backend is running.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Stack spacing={2}>
      {submitError && <Alert severity="error">{submitError}</Alert>}
      <Box component="form" onSubmit={onSubmit}>
        <Stack spacing={2}>
          <TextField
            label="Full name"
            name="full_name"
            autoComplete="name"
            error={nameError}
            helperText={nameErrorMessage}
            fullWidth
          />
          <TextField
            label="Email"
            type="email"
            name="email"
            autoComplete="email"
            error={emailError}
            helperText={emailErrorMessage}
            fullWidth
          />
          <PasswordField
            label="Password"
            name="password"
            autoComplete="new-password"
            error={passwordError}
            helperText={passwordErrorMessage}
            fullWidth
          />
          <PasswordField
            label="Confirm password"
            name="confirm_password"
            autoComplete="new-password"
            error={confirmPasswordError}
            helperText={confirmPasswordErrorMessage}
            fullWidth
          />
          <Button type="submit" variant="contained" size="large" disabled={isSubmitting} fullWidth>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </Stack>
      </Box>
      <Divider>or</Divider>
      <Button
        fullWidth
        variant="outlined"
        onClick={() => {
          window.location.href = `${API_BASE}/auth/google/login?mode=signup`;
        }}
        startIcon={<GoogleIcon />}
      >
        Sign up with Google
      </Button>
    </Stack>
  );
}

function authModeFromHash(hash: string): Mode | null {
  if (hash === "#auth-signup") return "signUp";
  if (hash === "#auth" || hash === "#auth-signin") return "signIn";
  return null;
}

export default function AuthSection() {
  const { loginWithToken, status, token } = useAuth();
  const navigate = useNavigate();
  const sectionRef = React.useRef<HTMLElement>(null);
  const [mode, setMode] = React.useState<Mode>(() => authModeFromHash(window.location.hash) ?? "signIn");
  const [successMsg, setSuccessMsg] = React.useState("");
  const [oauthError, setOauthError] = React.useState("");
  const [forgotOpen, setForgotOpen] = React.useState(false);
  const [rememberMe, setRememberMe] = React.useState<boolean>(shouldRememberSession());

  const isAuthenticated = status === "authenticated" && Boolean(token);

  React.useEffect(() => {
    const hash = window.location.hash.startsWith("#") ? window.location.hash : "";
    if (!hash) return;

    const params = new URLSearchParams(hash.slice(1));
    const accessToken = params.get("access_token");
    const error = params.get("error");

    if (accessToken) {
      loginWithToken(accessToken, rememberMe);
      window.history.replaceState(null, "", `${window.location.pathname}#auth`);
      navigate("/dashboard", { replace: true });
      return;
    }

    if (error) {
      setMode("signIn");
      setSuccessMsg("");
      setOauthError(`Google sign in failed: ${error.replaceAll("_", " ")}`);
      window.history.replaceState(null, "", `${window.location.pathname}#auth`);
      sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    const nextMode = authModeFromHash(hash);
    if (nextMode) {
      setMode(nextMode);
      sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [loginWithToken, navigate, rememberMe]);

  React.useEffect(() => {
    function onHashChange() {
      const nextMode = authModeFromHash(window.location.hash);
      if (nextMode) {
        setMode(nextMode);
        setSuccessMsg("");
      }
    }

    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function switchMode(nextMode: Mode) {
    setMode(nextMode);
    setSuccessMsg("");
    setOauthError("");
    const hash = nextMode === "signUp" ? "#auth-signup" : "#auth";
    if (window.location.hash !== hash) {
      window.history.replaceState(null, "", `${window.location.pathname}${hash}`);
    }
  }

  if (isAuthenticated) {
    return null;
  }

  return (
    <Box
      id="auth"
      ref={sectionRef}
      component="section"
      sx={{ scrollMarginTop: "calc(var(--template-frame-height, 0px) + 96px)" }}
    >
      <AuthShell
        sideContent={
          <AuthMarketingPanel
            appName="LanguageApp"
            eyebrow="Dutch micro-stories"
            title="Start reading Dutch with stories built around the words you need."
            description="Each story introduces 30% new vocabulary and recycles 70% known words — so you move from recognition to confident reading without overwhelm."
            highlights={[
              { value: "A1–C2", label: "CEFR-aligned progression" },
              { value: "70%", label: "Known-word recycling per story" },
              { value: "Daily", label: "Short sessions that fit your routine" },
            ]}
            points={[
              "Sign in to pick up your reading streak and dashboard progress.",
              "Create an account to unlock personalized stories and vocabulary tracking.",
            ]}
          />
        }
      >
        <Stack spacing={3}>
          <Box>
            <Typography variant="overline" color="primary.main">
              LanguageApp
            </Typography>
            <Typography variant="h4" sx={{ mt: 0.5 }}>
              {mode === "signIn" ? "Welcome back" : "Create your account"}
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1 }}>
              {mode === "signIn"
                ? "Sign in to continue your Dutch reading journey."
                : "Create an account to start learning through micro-stories."}
            </Typography>
          </Box>

          <Box
            sx={{
              p: 0.5,
              borderRadius: 1,
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: 0.5,
              bgcolor: "action.hover",
            }}
          >
            <Button variant={mode === "signIn" ? "contained" : "text"} onClick={() => switchMode("signIn")}>
              Sign in
            </Button>
            <Button variant={mode === "signUp" ? "contained" : "text"} onClick={() => switchMode("signUp")}>
              Create account
            </Button>
          </Box>

          {successMsg && <Alert severity="success">{successMsg}</Alert>}
          {oauthError && <Alert severity="error">{oauthError}</Alert>}

          <Collapse in={mode === "signIn"} unmountOnExit>
            <SignInForm
              onForgotOpen={() => setForgotOpen(true)}
              rememberMe={rememberMe}
              onRememberMeChange={setRememberMe}
            />
          </Collapse>

          <Collapse in={mode === "signUp"} unmountOnExit>
            <SignUpForm
              onSuccess={(email) => {
                setSuccessMsg(`Account created for ${email}. Redirecting to your dashboard...`);
                setMode("signIn");
              }}
            />
          </Collapse>

          <Typography variant="body2" color="text.secondary">
            By continuing, you agree to use LanguageApp for your personal language learning.
          </Typography>
        </Stack>
      </AuthShell>

      <ForgotPassword open={forgotOpen} handleClose={() => setForgotOpen(false)} />
    </Box>
  );
}
