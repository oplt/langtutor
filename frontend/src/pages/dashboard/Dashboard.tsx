import React from "react";
import { Outlet } from "react-router-dom";
import CssBaseline from "@mui/material/CssBaseline";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import AppNavbar from "./components/AppNavbar";
import SideMenu from "./components/SideMenu";
import AppTheme from "../shared-theme/AppTheme";
import { useAuth } from "../../context/AuthContext";
import { SessionDegradedBanner } from "../../shared/components/SessionDegradedBanner";
import { useFocusMainOnNavigate } from "../../shared/hooks/useFocusMainOnNavigate";
import { queryClient } from "../../shared/api/queryClient";
import { queryKeys } from "../../shared/api/queryKeys";
import {
  fetchLearningLevels,
  fetchProgressSummary,
} from "../../modules/learning/api/learningApi";

export default function Dashboard(props: { disableCustomTheme?: boolean }) {
  const { sessionDegraded, retrySession } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  const mainRef = useFocusMainOnNavigate();

  React.useEffect(() => {
    void queryClient.prefetchQuery({
      queryKey: queryKeys.learning.levels,
      queryFn: fetchLearningLevels,
    });
    void queryClient.prefetchQuery({
      queryKey: queryKeys.learning.progressSummary,
      queryFn: fetchProgressSummary,
    });
  }, []);

  return (
    <AppTheme {...props}>
      <CssBaseline enableColorScheme />
      {(sessionDegraded) && (
        <SessionDegradedBanner onRetry={retrySession} />
      )}
      <Box sx={{ display: "flex" }}>
        <SideMenu
          collapsed={sidebarCollapsed}
          onToggleCollapsed={() => setSidebarCollapsed((prev) => !prev)}
        />
        <AppNavbar />
        <Box
          component="main"
          ref={mainRef}
          tabIndex={-1}
          sx={{
            flexGrow: 1,
            bgcolor: 'background.default',
            overflow: 'auto',
            outline: 'none',
          }}
        >
          <Stack
            spacing={2}
            sx={{
              alignItems: "center",
              px: { xs: 2, md: 3 },
              pb: { xs: 4, md: 6 },
              mt: { xs: 8, md: 0 },
            }}
          >
            {/* This is where pages will render */}
            <Outlet />
          </Stack>
        </Box>
      </Box>
    </AppTheme>
  );
}
