import { useState, useEffect, useCallback, createContext, useContext } from "react";
import { rpc } from "../api/rpc";

export type ThemeChoice = "light" | "dark" | "system";

function getSystemTheme(): "light" | "dark" {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolveTheme(choice: ThemeChoice): "light" | "dark" {
  return choice === "system" ? getSystemTheme() : choice;
}

function applyTheme(resolved: "light" | "dark") {
  document.documentElement.classList.toggle("dark", resolved === "dark");
  // Windows and Linux draw the window buttons on the toolbar: give them its colours.
  const style = getComputedStyle(document.documentElement);
  window.tuttle?.setTitleBarColors({
    color: style.getPropertyValue("--color-bg-content").trim(),
    symbolColor: style.getPropertyValue("--color-primary").trim(),
  });
}

function cacheChoice(choice: ThemeChoice) {
  try { localStorage.setItem("tuttle-theme", choice); } catch { /* noop */ }
}

function getCachedChoice(): ThemeChoice | null {
  try {
    const v = localStorage.getItem("tuttle-theme");
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch { /* noop */ }
  return null;
}

interface ThemeContextValue {
  choice: ThemeChoice;
  resolved: "light" | "dark";
  setChoice: (next: ThemeChoice) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  choice: "dark",
  resolved: "dark",
  setChoice: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

export { ThemeContext };

export function useThemeProvider() {
  const [choice, setChoiceState] = useState<ThemeChoice>(() => getCachedChoice() ?? "dark");
  const resolved = resolveTheme(choice);

  useEffect(() => {
    rpc<{ theme_mode?: string }>("preferences.get").then((res) => {
      if (res.ok && res.data?.theme_mode) {
        const mode = res.data.theme_mode as ThemeChoice;
        if (mode === "light" || mode === "dark" || mode === "system") {
          setChoiceState(mode);
          cacheChoice(mode);
          applyTheme(resolveTheme(mode));
        }
      }
    });
  }, []);

  const setChoice = useCallback((next: ThemeChoice) => {
    setChoiceState(next);
    cacheChoice(next);
    applyTheme(resolveTheme(next));
    rpc("preferences.save", { theme_mode: next });
  }, []);

  useEffect(() => {
    applyTheme(resolved);
  }, [resolved]);

  // Forcing a theme also forces prefers-color-scheme, so this runs before
  // the listener below subscribes: releasing it back to "system" then
  // arrives there as a change.
  useEffect(() => {
    window.tuttle?.setThemeSource(choice);
  }, [choice]);

  useEffect(() => {
    if (choice !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => applyTheme(getSystemTheme());
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [choice]);

  return { choice, resolved, setChoice } as const;
}
