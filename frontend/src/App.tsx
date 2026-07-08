import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Verify from "./pages/Verify";
import Schemas from "./pages/Schemas";

export default function App() {
  const { username, ready } = useAuth();

  if (!ready) {
    return <div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>;
  }

  if (!username) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/verify" element={<Verify />} />
        <Route path="/schemas" element={<Schemas />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
