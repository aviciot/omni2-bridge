"use client";

import { useEffect, useState } from "react";
import ChatWidget from "./ChatWidget";

export default function ChatWidgetWrapper() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check if user has token in localStorage
    const checkAuth = () => {
      const token = localStorage.getItem("access_token");
      setIsAuthenticated(!!token);
    };

    checkAuth();

    // Listen for storage changes (login/logout in other tabs)
    window.addEventListener("storage", checkAuth);
    
    // Listen for custom auth events
    window.addEventListener("auth-change", checkAuth);

    return () => {
      window.removeEventListener("storage", checkAuth);
      window.removeEventListener("auth-change", checkAuth);
    };
  }, []);

  if (!isAuthenticated) {
    return null;
  }

  return <ChatWidget />;
}
