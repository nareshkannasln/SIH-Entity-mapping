import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth";
import { ThemeProvider } from "./lib/theme";
import { VerificationRunProvider } from "./lib/verificationRun";
import { ToastProvider } from "./components/Toast";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <ToastProvider>
        <BrowserRouter>
          <AuthProvider>
            {/* Above the router on purpose: an in-flight verification must not be
                torn down just because the user switches page. */}
            <VerificationRunProvider>
              <App />
            </VerificationRunProvider>
          </AuthProvider>
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  </React.StrictMode>
);
