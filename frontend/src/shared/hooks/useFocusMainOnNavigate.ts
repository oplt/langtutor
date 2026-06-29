import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Overview",
  "/dashboard/tasks": "Practice tasks",
  "/dashboard/analytics": "Progress analytics",
  "/dashboard/routine": "Study plan",
  "/dashboard/documents": "Study documents",
  "/dashboard/reading": "Reading",
  "/dashboard/coach": "AI tutor",
  "/dashboard/settings": "Settings",
  "/dashboard/profile": "Profile",
  "/dashboard/account": "Account",
};

function titleForPath(pathname: string): string {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  const match = Object.entries(PAGE_TITLES).find(([path]) => pathname.startsWith(`${path}/`));
  return match?.[1] ?? "Dashboard";
}

/** Move keyboard focus to main content when the dashboard route changes. */
export function useFocusMainOnNavigate() {
  const mainRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();

  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;
    const pageTitle = titleForPath(pathname);
    el.setAttribute("aria-label", `${pageTitle} content`);
    el.focus({ preventScroll: true });
  }, [pathname]);

  return mainRef;
}
