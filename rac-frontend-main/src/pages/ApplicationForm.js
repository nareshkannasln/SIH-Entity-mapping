import React, { useState } from "react";
import { useNavigate } from "react-router-dom"; // Assuming you are using React Router
import axios from "axios"; // Ensure you have axios imported
import "./ApplicationForm.css";
import { v4 as uuidv4 } from "uuid";
function ApplicationForm() {
  const [formData, setFormData] = useState({
    applicationId: uuidv4(),
    name: "",
    email: "",
    phone: "",
    job: "",
    education: "",
    gateScore: "",
    password: "", // This is a string now, not a file
  });

  const [isSubmitting, setIsSubmitting] = useState(false); // Track submission state
  const [isSubmitted, setIsSubmitted] = useState(false); // Track if form has been successfully submitted
  const [errorMessage, setErrorMessage] = useState(""); // Track error message for display
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true); // Set submitting state to true while the form is being processed

    try {
      const formDataToUpload = new FormData();
      formDataToUpload.append("applicationId",formData.applicationId);
      formDataToUpload.append("name", formData.name);
      formDataToUpload.append("email", formData.email);
      formDataToUpload.append("phone", formData.phone);
      formDataToUpload.append("job", formData.job);
      formDataToUpload.append("education", formData.education);
      formDataToUpload.append("gateScore", formData.gateScore);
      formDataToUpload.append("password", formData.password); // Sending password as a string

      // Replace the URL below with your backend API endpoint
      const response = await axios.post("http://localhost:8000/submit-application/", formDataToUpload, {
        headers: {
          "Content-Type": "multipart/form-data", // This ensures the form data is sent as multipart
        },
      });

      if (response.status === 200) {
        setIsSubmitted(true); // Mark the form as submitted
        setTimeout(() => {
          navigate("/ocr-upload"); // Navigate to the file upload page after a successful submission
        }, 2000); // Wait for 2 seconds before navigating (for a smooth experience)
      } else {
        throw new Error("Failed to submit application, please try again.");
      }
    } catch (error) {
      console.error("Error submitting application:", error);
      // Check if the error response contains a message from the backend
      if (error.response && error.response.data) {
        setErrorMessage(error.response.data.message || "An unknown error occurred.");
      } else {
        setErrorMessage("There was an issue submitting your application.");
      }
    } finally {
      setIsSubmitting(false); // Reset submitting state
    }
  };

  return (
    <div className="application-form-container">
      <h1>Apply for DRDO RAC Job</h1>

      {/* If the form has been submitted, show a success message */}
      {isSubmitted ? (
        <div className="submission-success">
          <h2>Application Submitted Successfully!</h2>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label>Name:</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              disabled={isSubmitting} // Disable input while submitting
            />
          </div>
          <div className="form-field">
            <label>Email:</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              disabled={isSubmitting} // Disable input while submitting
            />
          </div>
          <div className="form-field">
            <label>Phone:</label>
            <input
              type="text"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              required
              disabled={isSubmitting} // Disable input while submitting
            />
          </div>
          <div className="form-field">
            <label>Job Position:</label>
            <select
              name="job"
              value={formData.job}
              onChange={handleChange}
              required
              disabled={isSubmitting} // Disable select while submitting
            >
              <option value="JRF">Junior Research Fellow (JRF)</option>
              <option value="RA">Research Associate (RA)</option>
              <option value="PA">Project Assistant</option>
            </select>
          </div>
          <div className="form-field">
            <label>Education:</label>
            <input
              type="text"
              name="education"
              value={formData.education}
              onChange={handleChange}
              required
              disabled={isSubmitting} // Disable input while submitting
            />
          </div>
          <div className="form-field">
            <label>Gate Score:</label>
            <input
              type="number"
              name="gateScore"
              value={formData.gateScore}
              onChange={handleChange}
              required
              disabled={isSubmitting} // Disable input while submitting
            />
          </div>
          <div className="form-field">
            <label>Password:</label>
            <input
              type="text"
              name="password" // Simple text input for password
              value={formData.password}
              onChange={handleChange}
              required
              disabled={isSubmitting} // Disable input while submitting
            />
          </div>

          {/* Show the submit button or a loading state */}
          <div className="form-buttons">
            {isSubmitting ? (
              <button type="button" disabled>
                Submitting...
              </button>
            ) : (
              <button type="submit">Submit Application</button>
            )}
          </div>
        </form>
      )}

      {/* Show error message */}
      {errorMessage && (
        <div className="error-message">
          <p style={{ color: "red" }}>{errorMessage}</p>
        </div>
      )}
    </div>
  );
}

export default ApplicationForm;
