import React, { useState } from "react";
import { useLocation } from "react-router-dom";

const OCRPage = () => {
  const location = useLocation(); // Access location state passed from the form
  const { applicationId, name } = location.state || {}; // Extract applicationId and name

  const [files, setFiles] = useState({
    aadhar: null,
    pan: null,
    communityCertificate: null,
    pwdCertificate: null,
    gateScoreCard: null,
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Handle file change for each document
  const handleFileChange = (e, fieldName) => {
    const newFiles = { ...files };
    newFiles[fieldName] = e.target.files[0];  // Update the specific file
    setFiles(newFiles);
  };

  // Function to upload each file separately
  const handleUpload = async (file, fieldName) => {
    if (!file) {
      setError(`Please select a file for ${fieldName}.`);
      return;
    }

    // Ensure name and applicationId are included in the request
    if (!name || !applicationId) {
      setError("Name or Application ID is missing.");
      return;
    }

    const formData = new FormData();
    formData.append("applicationId", applicationId); // Include applicationId
    formData.append("name", name);  // Include name
    formData.append("file", file);  // Include the specific file to FormData

    try {
      const response = await fetch("http://localhost:8000/upload/", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setMessage(`${fieldName} file uploaded successfully.`);
        setError("");  // Clear any existing error messages
      } else {
        setError(result.message || `Error uploading ${fieldName}.`);
        setMessage("");  // Clear any existing success messages
      }
    } catch (err) {
      setError(`An error occurred while uploading ${fieldName}.`);
      setMessage("");  // Clear any existing success messages
    }
  };

  return (
    <div>
      <h1>Upload Your Documents</h1>

      {/* Aadhar File Upload */}
      <div>
        <label htmlFor="aadharFile">Upload Aadhar:</label>
        <input
          id="aadharFile"
          type="file"
          onChange={(e) => handleFileChange(e, "aadhar")}
        />
        <button onClick={() => handleUpload(files.aadhar, "Aadhar")}>
          Upload Aadhar
        </button>
      </div>

      {/* PAN File Upload */}
      <div>
        <label htmlFor="panFile">Upload PAN:</label>
        <input
          id="panFile"
          type="file"
          onChange={(e) => handleFileChange(e, "pan")}
        />
        <button onClick={() => handleUpload(files.pan, "PAN")}>
          Upload PAN
        </button>
      </div>

      {/* Community Certificate File Upload */}
      <div>
        <label htmlFor="communityFile">Upload Community Certificate:</label>
        <input
          id="communityFile"
          type="file"
          onChange={(e) => handleFileChange(e, "communityCertificate")}
        />
        <button
          onClick={() =>
            handleUpload(files.communityCertificate, "Community Certificate")
          }
        >
          Upload Community Certificate
        </button>
      </div>

      {/* PWD Certificate File Upload */}
      <div>
        <label htmlFor="pwdFile">Upload PWD Certificate:</label>
        <input
          id="pwdFile"
          type="file"
          onChange={(e) => handleFileChange(e, "pwdCertificate")}
        />
        <button
          onClick={() => handleUpload(files.pwdCertificate, "PWD Certificate")}
        >
          Upload PWD Certificate
        </button>
      </div>

      {/* GATE Score Card File Upload */}
      <div>
        <label htmlFor="gateScoreCardFile">Upload GATE Score Card:</label>
        <input
          id="gateScoreCardFile"
          type="file"
          onChange={(e) => handleFileChange(e, "gateScoreCard")}
        />
        <button
          onClick={() =>
            handleUpload(files.gateScoreCard, "GATE Score Card")
          }
        >
          Upload GATE Score Card
        </button>
      </div>

      {/* Display error if any */}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Display success message */}
      {message && <p style={{ color: "green" }}>{message}</p>}
    </div>
  );
};

export default OCRPage;
