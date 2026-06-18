import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoute";
import { PageLoading } from "./shared/components/PageLoading";

const Home = lazy(() => import("./pages/Home/Home"));
const Dashboard = lazy(() => import("./pages/dashboard/Dashboard"));
const DashboardHome = lazy(() => import("./pages/dashboard/tabs/HomePage"));
const TasksPage = lazy(() => import("./pages/dashboard/tabs/TasksPage"));
const SettingsPage = lazy(() => import("./pages/dashboard/tabs/SettingsPage"));
const AnalyticsPage = lazy(() => import("./pages/dashboard/tabs/AnalyticsPage"));
const RoutinePage = lazy(() => import("./pages/dashboard/tabs/RoutinePage"));
const CoachPage = lazy(() => import("./pages/dashboard/tabs/CoachPage"));
const ProfilePage = lazy(() => import("./pages/dashboard/tabs/ProfilePage"));
const AccountPage = lazy(() => import("./pages/dashboard/tabs/AccountPage"));

function PageFallback() {
  return <PageLoading label="Loading page…" />;
}

export default function App() {
  return (
    <BrowserRouter future={{
                       v7_relativeSplatPath: true,
                     }}>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Navigate to="/#auth" replace />} />
          <Route path="/signin" element={<Navigate to="/#auth" replace />} />
          <Route path="/signup" element={<Navigate to="/#auth-signup" replace />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardHome />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="routine" element={<RoutinePage />} />
            <Route path="coach" element={<CoachPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="account" element={<AccountPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
