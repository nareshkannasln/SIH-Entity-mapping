import React from "react";
import ReactDOM from "react-dom/client";  // Import createRoot from 'react-dom/client'
import App from "./App";
import "./styles/App.css"; // Import your global styles

// Create a root container and render the App component inside it
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
