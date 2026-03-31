/**
 * CV Client for interacting with the CV Evaluation API
 * A JavaScript module for evaluating CVs via text or file upload
 */

export class CvClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
    this.apiEndpoint = "/api/cv/evaluate";
  }

  /**
   * Evaluate CV from text content
   * @param {string} cvText - The CV content as text
   * @returns {Promise<Object>} - API response
   */
  async evaluateText(cvText) {
    if (!cvText || typeof cvText !== "string") {
      throw new Error("CV text is required and must be a string");
    }

    try {
      const formData = new FormData();
      formData.append("cv_text", cvText);

      const response = await fetch(`${this.baseUrl}${this.apiEndpoint}`, {
        method: "POST",
        body: formData,
      });

      return await this._handleResponse(response);
    } catch (error) {
      throw new Error(`Failed to evaluate CV text: ${error.message}`);
    }
  }

  /**
   * Evaluate CV from file upload
   * @param {File} file - The CV file to upload
   * @returns {Promise<Object>} - API response
   */
  async evaluateFile(file) {
    if (!file || !(file instanceof File)) {
      throw new Error("A valid file is required");
    }

    // Check file type
    const allowedTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ];

    if (!allowedTypes.includes(file.type)) {
      throw new Error("Unsupported file type. Please upload PDF or DOCX files only.");
    }

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${this.baseUrl}${this.apiEndpoint}`, {
        method: "POST",
        body: formData,
      });

      return await this._handleResponse(response);
    } catch (error) {
      throw new Error(`Failed to evaluate CV file: ${error.message}`);
    }
  }

  /**
   * Generic evaluate method that handles both text and file input
   * @param {string|File} input - Either CV text string or File object
   * @returns {Promise<Object>} - API response
   */
  async evaluate(input) {
    if (typeof input === "string") {
      return this.evaluateText(input);
    } else if (input instanceof File) {
      return this.evaluateFile(input);
    } else {
      throw new Error("Input must be either a string (CV text) or File object");
    }
  }

  /**
   * Private method to handle API responses
   * @private
   * @param {Response} response - Fetch response object
   * @returns {Promise<Object>} - Parsed JSON response
   */
  async _handleResponse(response) {
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch (e) {
        // If we can't parse the error response, use the default message
      }

      throw new Error(errorMessage);
    }

    try {
      return await response.json();
    } catch (error) {
      throw new Error("Failed to parse response as JSON");
    }
  }

  /**
   * Get supported file types
   * @returns {Array<string>} - Array of supported MIME types
   */
  static getSupportedFileTypes() {
    return [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ];
  }

  /**
   * Validate file before upload
   * @param {File} file - File to validate
   * @returns {boolean} - True if file is valid
   */
  static validateFile(file) {
    if (!file || !(file instanceof File)) {
      return false;
    }

    const supportedTypes = CvClient.getSupportedFileTypes();
    return supportedTypes.includes(file.type);
  }
}

// Export as default as well for convenience
export default CvClient;
