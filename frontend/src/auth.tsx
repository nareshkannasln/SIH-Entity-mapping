import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, token } from "./api";

interface AuthState {
  username: string | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!token.get()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then((u) => setUsername(u.username))
      .catch(() => token.clear())
      .finally(() => setReady(true));
  }, []);

  const login = async (u: string, p: string) => {
    const { access_token } = await api.login(u, p);
    token.set(access_token);
    const me = await api.me();
    setUsername(me.username);
  };

  const register = async (u: string, e: string, p: string) => {
    const { access_token } = await api.register(u, e, p);
    token.set(access_token);
    const me = await api.me();
    setUsername(me.username);
  };

  const logout = () => {
    token.clear();
    setUsername(null);
  };

  return (
    <AuthContext.Provider value={{ username, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
