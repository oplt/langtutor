import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

/** Move keyboard focus to main content when the dashboard route changes. */
export function useFocusMainOnNavigate() {
  const mainRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();

  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true });
  }, [pathname]);

  return mainRef;
}
