import * as React from 'react';
import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Container from '@mui/material/Container';
import Divider from '@mui/material/Divider';
import MenuItem from '@mui/material/MenuItem';
import Drawer from '@mui/material/Drawer';
import Typography from '@mui/material/Typography';
import MenuIcon from '@mui/icons-material/Menu';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import { Link as RouterLink } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import { tesla } from '../../shared-theme/themePrimitives';

const StyledToolbar = styled(Toolbar)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  flexShrink: 0,
  borderRadius: theme.shape.borderRadius,
  backdropFilter: 'blur(12px)',
  border: 'none',
  backgroundColor: tesla.frostGlass,
  boxShadow: 'none',
  padding: '8px 12px',
  minHeight: 48,
}));

export default function AppAppBar() {
  const [open, setOpen] = React.useState(false);
  const { status, token, logout } = useAuth();
  const isAuthenticated = status === "authenticated" && Boolean(token);

  const toggleDrawer = (newOpen: boolean) => () => {
    setOpen(newOpen);
  };

  return (
    <AppBar
      position="fixed"
      enableColorOnDark
      sx={{
        boxShadow: 0,
        bgcolor: 'transparent',
        backgroundImage: 'none',
        mt: 'calc(var(--template-frame-height, 0px) + 28px)',
      }}
    >
      <Container maxWidth="lg">
        <StyledToolbar variant="dense" disableGutters>
          <Typography
            variant="subtitle2"
            component={RouterLink}
            to="/"
            sx={{
              letterSpacing: '0.12em',
              color: 'text.primary',
              textDecoration: 'none',
              fontWeight: 500,
            }}
          >
            LANGUAGEAPP
          </Typography>
          <Box
            sx={{
              display: { xs: 'none', md: 'flex' },
              gap: 0.5,
              alignItems: 'center',
            }}
          >
            <IconButton
              aria-label="Go to homepage"
              component={RouterLink}
              to="/"
              size="small"
            >
              <HomeRoundedIcon fontSize="small" />
            </IconButton>
            {isAuthenticated ? (
              <>
                <Button color="primary" variant="contained" size="small" component={RouterLink} to="/dashboard">
                  Dashboard
                </Button>
                <Button color="primary" variant="outlined" size="small" onClick={logout}>
                  Sign out
                </Button>
              </>
            ) : (
              <>

              </>
            )}
          </Box>
          <Box sx={{ display: { xs: 'flex', md: 'none' }, gap: 1 }}>
            <IconButton aria-label="Go to homepage" component={RouterLink} to="/">
              <HomeRoundedIcon />
            </IconButton>
            <IconButton aria-label="Menu button" onClick={toggleDrawer(true)}>
              <MenuIcon />
            </IconButton>
            <Drawer
              anchor="top"
              open={open}
              onClose={toggleDrawer(false)}
              PaperProps={{
                sx: {
                  top: 'var(--template-frame-height, 0px)',
                  boxShadow: 'none',
                },
              }}
            >
              <Box sx={{ p: 2, backgroundColor: 'background.default' }}>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <IconButton onClick={toggleDrawer(false)}>
                    <CloseRoundedIcon />
                  </IconButton>
                </Box>
                <Divider sx={{ my: 3 }} />
                {isAuthenticated ? (
                  <>
                    <MenuItem>
                      <Button color="primary" variant="contained" component={RouterLink} to="/dashboard" fullWidth>
                        Dashboard
                      </Button>
                    </MenuItem>
                    <MenuItem>
                      <Button
                        color="primary"
                        variant="outlined"
                        fullWidth
                        onClick={() => {
                          logout();
                          setOpen(false);
                        }}
                      >
                        Sign out
                      </Button>
                    </MenuItem>
                  </>
                ) : (
                  <>
                    <MenuItem>
                      <Button color="primary" variant="text" href="#how-it-works" fullWidth>
                        Method
                      </Button>
                    </MenuItem>
                    <MenuItem>
                      <Button color="primary" variant="contained" component={RouterLink} to="/#auth-signup" fullWidth>
                        Sign up
                      </Button>
                    </MenuItem>
                    <MenuItem>
                      <Button color="primary" variant="outlined" component={RouterLink} to="/#auth" fullWidth>
                        Sign in
                      </Button>
                    </MenuItem>
                  </>
                )}
              </Box>
            </Drawer>
          </Box>
        </StyledToolbar>
      </Container>
    </AppBar>
  );
}
