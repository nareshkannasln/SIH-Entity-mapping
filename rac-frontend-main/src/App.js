import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar"; // Navbar component
import Footer from "./components/Footer"; // Footer component
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import ApplicantPage from "./pages/ApplicantPage";
import AdminPage from "./pages/AdminPage";
import ApplicationForm from "./pages/ApplicationForm";
import OCRPage from "./pages/ocr-upload"; // Add this import for the file upload page

function App() {
  return (
    <Router>
      {/* Navbar will be displayed on every page */}
      <Navbar />

      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/applicant" element={<ApplicantPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/application-form" element={<ApplicationForm />} />
          <Route path="/ocr-upload" element={<OCRPage />} /> {/* Add route for OCR upload */}
        </Routes>
      </main>

      {/* Footer will be displayed on every page */}
      
    </Router>
  );
}

export default App;
