import { useEffect, useRef, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth";
import { useTheme } from "../lib/theme";
import {
  IconGrid,
  IconLayers,
  IconLogout,
  IconMoon,
  IconScan,
  IconSettings,
  IconShield,
  IconSun,
} from "./icons";

const nav = [
  { to: "/", label: "Dashboard", icon: IconGrid, end: true },
  { to: "/verify", label: "Verify", icon: IconScan, end: false },
  { to: "/schemas", label: "Doc Types", icon: IconLayers, end: false },
];

function linkClass({ isActive }: { isActive: boolean }) {
  return `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300"
      : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
  }`;
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? <IconSun width={18} height={18} /> : <IconMoon width={18} height={18} />}
    </button>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { username, isAdmin, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close the menu on an outside press or Escape.
  //
  // This deliberately does NOT use onBlur + setTimeout on the trigger: blur
  // fires on mousedown, so a click held longer than the timeout unmounted the
  // menu before mouseup, no click event was ever produced, and "Log out" did
  // nothing. Anchoring to presses *outside* menuRef removes the race — a press
  // on an item can never close the menu before its click lands.
  useEffect(() => {
    if (!menuOpen) return;

    const onPointerDown = (e: PointerEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto flex max-w-6xl items-center gap-1 px-4 py-2.5">
          <NavLink to="/" className="mr-3 flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm">
              <IconShield width={18} height={18} />
            </span>
            <span className="text-base font-bold tracking-tight">
              Doc<span className="text-indigo-600 dark:text-indigo-400">Verify</span>
            </span>
          </NavLink>

          <nav className="hidden items-center gap-1 sm:flex">
            {nav.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass}>
                <Icon width={16} height={16} />
                {label}
              </NavLink>
            ))}
            {isAdmin && (
              <NavLink to="/settings" className={linkClass}>
                <IconSettings width={16} height={16} />
                Settings
              </NavLink>
            )}
          </nav>

          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen((o) => !o)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <span className="grid h-7 w-7 place-items-center rounded-full bg-slate-200 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
                  {username?.[0]?.toUpperCase() ?? "?"}
                </span>
                <span className="hidden max-w-[10rem] truncate font-medium text-slate-700 dark:text-slate-200 md:block">
                  {username}
                </span>
              </button>
              {menuOpen && (
                <div className="animate-fade-in absolute right-0 mt-1 w-44 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-slate-900">
                  <NavLink
                    to="/profile"
                    onClick={() => setMenuOpen(false)}
                    className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Profile & security
                  </NavLink>
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      logout();
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
                  >
                    <IconLogout width={16} height={16} />
                    Log out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Mobile nav */}
        <nav className="flex items-center gap-1 overflow-x-auto border-t border-slate-200 px-3 py-1.5 sm:hidden dark:border-slate-800">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass}>
              <Icon width={16} height={16} />
              {label}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink to="/settings" className={linkClass}>
              <IconSettings width={16} height={16} />
              Settings
            </NavLink>
          )}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
