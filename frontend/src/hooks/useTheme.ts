import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

function readInitialTheme(): Theme {
  if (typeof document !== "undefined") {
    const attr = document.documentElement.getAttribute("data-theme");
    if (attr === "light" || attr === "dark") return attr;
  }
  return "light";
}

/**
 * Theme state synced to <html data-theme> and persisted to localStorage.
 * The initial value is whatever the pre-paint inline script in index.html set,
 * so there is no flash.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("viewer-theme", theme);
    } catch {
      /* localStorage may be unavailable; non-fatal */
    }
  }, [theme]);

  const toggleTheme = useCallback(() => setTheme((current) => (current === "dark" ? "light" : "dark")), []);

  return { theme, toggleTheme };
}
