import React, { useState } from "react";

function DocumentUpload() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setMessage(""); // Reset message on file selection
  };

  const handleUpload = () => {
    if (file) {
      setMessage(`File "${file.name}" is being uploaded...`);
      // Simulate upload with a timeout
      setTimeout(() => {
        setMessage(`File "${file.name}" uploaded successfully.`);
      }, 2000);
    } else {
      setMessage("Please select a file to upload.");
    }
  };

  return (
    <div className="document-upload">
      <h2>Upload Your Document</h2>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload}>Upload</button>
      <p>{message}</p>
    </div>
  );
}

export default DocumentUpload;
