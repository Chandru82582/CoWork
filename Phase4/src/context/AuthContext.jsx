import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { login as apiLogin, registerUnauthorizedHandler } from "../api/client.js";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("signal_token"));
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const logout = useCallback(() => {
    localStorage.removeItem("signal_token");
    setToken(null);
  }, []);

  useEffect(() => {
    registerUnauthorizedHandler(logout);
  }, [logout]);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await apiLogin(username, password);
      localStorage.setItem("signal_token", access_token);
      setToken(access_token);
    } catch (e) {
      setError(
        e?.response?.data?.detail || "Login failed. Check the username and password."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({ token, isAuthenticated: !!token, login, logout, error, loading }),
    [token, login, logout, error, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
