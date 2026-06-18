import * as React from 'react';
import { styled } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import MuiDrawer, { drawerClasses } from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Collapse from '@mui/material/Collapse';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import MoreVertRoundedIcon from '@mui/icons-material/MoreVertRounded';
import MenuOpenRoundedIcon from '@mui/icons-material/MenuOpenRounded';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import MenuContent from './MenuContent';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLogout } from '../../../shared/hooks/useLogout';

const expandedDrawerWidth = 240;
const collapsedDrawerWidth = 80;

const Drawer = styled(MuiDrawer)<{ collapsed?: boolean }>(({ collapsed }) => ({
  width: collapsed ? collapsedDrawerWidth : expandedDrawerWidth,
  flexShrink: 0,
  boxSizing: 'border-box',
  mt: 10,
  [`& .${drawerClasses.paper}`]: {
    width: collapsed ? collapsedDrawerWidth : expandedDrawerWidth,
    boxSizing: 'border-box',
    transition: 'width 180ms ease',
  },
}));

type SideMenuProps = {
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
};

export default function SideMenu({ collapsed = false, onToggleCollapsed }: SideMenuProps) {
  const [menuOpen, setMenuOpen] = React.useState(false);
  const { user } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();
  const initials = (user?.full_name || user?.email || "U").trim().charAt(0).toUpperCase();

  React.useEffect(() => {
    if (collapsed) {
      setMenuOpen(false);
    }
  }, [collapsed]);

  const handleAction = (path: string) => () => {
    navigate(path);
    setMenuOpen(false);
  };
  const handleLogout = () => {
    logout();
    setMenuOpen(false);
  };

  return (
    <Drawer
      collapsed={collapsed}
      variant="permanent"
      sx={{
        display: { xs: 'none', md: 'block' },
        width: collapsed ? collapsedDrawerWidth : expandedDrawerWidth,
        [`& .${drawerClasses.paper}`]: {
          backgroundColor: 'background.paper',
        },
      }}
    >
      <Box
        sx={{
          overflow: 'auto',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Stack
          direction="row"
          sx={{
            px: collapsed ? 1 : 1.5,
            py: 1,
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'space-between',
          }}
        >
          {!collapsed && (
            <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
              Navigation
            </Typography>
          )}
          <IconButton size="small" aria-label="Toggle sidebar" onClick={onToggleCollapsed}>
            {collapsed ? <MenuRoundedIcon fontSize="small" /> : <MenuOpenRoundedIcon fontSize="small" />}
          </IconButton>
        </Stack>
        <MenuContent collapsed={collapsed} />

      </Box>
      <Stack sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
        <Collapse in={menuOpen && !collapsed} timeout="auto" unmountOnExit>
          <Stack sx={{ px: 1, pt: 1, pb: 0.5 }} spacing={0.5}>
            <Button fullWidth size="small" onClick={handleAction('/dashboard/profile')} sx={{ justifyContent: 'flex-start' }}>
              Profile
            </Button>
            <Button fullWidth size="small" onClick={handleAction('/dashboard/account')} sx={{ justifyContent: 'flex-start' }}>
              My account
            </Button>
            <Button fullWidth size="small" onClick={handleAction('/dashboard/settings')} sx={{ justifyContent: 'flex-start' }}>
              Settings
            </Button>
            <Button fullWidth size="small" color="error" onClick={handleLogout} sx={{ justifyContent: 'flex-start' }}>
              Logout
            </Button>
          </Stack>
        </Collapse>
        <Stack
          direction="row"
          role="button"
          tabIndex={0}
          aria-label="Toggle user menu"
          onClick={() => setMenuOpen((prev) => !prev)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setMenuOpen((prev) => !prev);
            }
          }}
          sx={{
            p: 2,
            gap: 1,
            alignItems: 'center',
            cursor: 'pointer',
            '&:hover': {
              bgcolor: 'action.hover',
            },
          }}
        >
          <Avatar
            alt={user?.full_name || user?.email || "Language learner"}
            sx={{ width: 36, height: 36 }}
          >
            {initials}
          </Avatar>
          {!collapsed && (
            <Box sx={{ mr: 'auto', minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: '16px' }} noWrap>
              {user?.full_name || "Language learner"}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }} noWrap>
              {user?.email || "user@email.com"}
            </Typography>
          </Box>
        )}
          {!collapsed && <MoreVertRoundedIcon fontSize="small" color="action" />}
        </Stack>
      </Stack>
    </Drawer>
  );
}
