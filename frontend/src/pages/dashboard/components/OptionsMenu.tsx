import * as React from 'react';
import { styled } from '@mui/material/styles';
import Divider, { dividerClasses } from '@mui/material/Divider';
import Menu from '@mui/material/Menu';
import MuiMenuItem from '@mui/material/MenuItem';
import { paperClasses } from '@mui/material/Paper';
import { listClasses } from '@mui/material/List';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon, { listItemIconClasses } from '@mui/material/ListItemIcon';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import MoreVertRoundedIcon from '@mui/icons-material/MoreVertRounded';
import MenuButton from './MenuButton';
import { useNavigate } from 'react-router-dom';
import { useLogout } from '../../../shared/hooks/useLogout';

const MenuItem = styled(MuiMenuItem)({
  margin: '2px 0',
});

type OptionsMenuProps = {
  renderTrigger?: (onClick: (event: React.MouseEvent<HTMLElement>) => void) => React.ReactNode;
};

export default function OptionsMenu({ renderTrigger }: OptionsMenuProps) {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const logout = useLogout();
  const navigate = useNavigate();
  const open = Boolean(anchorEl);
  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const handleNavigate = (path: string) => () => {
    navigate(path);
    handleClose();
  };
  const handleLogout = () => {
    logout();
    handleClose();
  };
  return (
    <React.Fragment>
      {renderTrigger ? (
        renderTrigger(handleClick)
      ) : (
        <MenuButton
          aria-label="Open menu"
          onClick={handleClick}
          sx={{ borderColor: 'transparent' }}
        >
          <MoreVertRoundedIcon />
        </MenuButton>
      )}
      <Menu
        anchorEl={anchorEl}
        id="menu"
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'top' }}
        sx={{
          [`& .${listClasses.root}`]: {
            padding: '4px',
          },
          [`& .${paperClasses.root}`]: {
            padding: 0,
          },
          [`& .${dividerClasses.root}`]: {
            margin: '4px -4px',
          },
        }}
      >
        <MenuItem onClick={handleNavigate("/dashboard/profile")}>Profile</MenuItem>
        <MenuItem onClick={handleNavigate("/dashboard/account")}>My account</MenuItem>
        <Divider />
        <MenuItem onClick={handleNavigate("/dashboard/settings")}>Settings</MenuItem>
        <Divider />
        <MenuItem
          onClick={handleLogout}
          sx={{
            [`& .${listItemIconClasses.root}`]: {
              ml: 'auto',
              minWidth: 0,
            },
          }}
        >
          <ListItemText>Logout</ListItemText>
          <ListItemIcon>
            <LogoutRoundedIcon fontSize="small" />
          </ListItemIcon>
        </MenuItem>
      </Menu>
    </React.Fragment>
  );
}
