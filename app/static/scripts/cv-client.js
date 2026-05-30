/**
 * CV Client for interacting with the CV Evaluation API
 * A JavaScript module for evaluating CVs with optional job descriptions
 */

export class CvClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
    this.apiEndpoint = "/api/cv/evaluate";
  }

  async evaluateSubmission({ cv, jd }) {
    this._validateRequiredInput(cv, "CV");
    if (jd) {
      this._validateOptionalInput(jd, "job description");
    }

    try {
      const formData = new FormData();
      this._appendInput(formData, cv, "cv");
      if (jd && this._hasInput(jd)) {
        this._appendInput(formData, jd, "jd");
      }

      const response = await fetch(`${this.baseUrl}${this.apiEndpoint}`, {
        method: "POST",
        body: formData,
      });

      return await this._handleResponse(response);
    } catch (error) {
      throw new Error(`Failed to evaluate submission: ${error.message}`);
    }
  }

  _appendInput(formData, input, prefix) {
    if (input.mode === "text") {
      formData.append(`${prefix}_text`, input.text.trim());
    } else {
      formData.append(`${prefix}_file`, input.file);
    }
  }

  _hasInput(input) {
    if (input.mode === "text") {
      return typeof input.text === "string" && input.text.trim().length > 0;
    }
    return input.file instanceof File;
  }

  _validateRequiredInput(input, inputName) {
    if (!input || (input.mode !== "text" && input.mode !== "file")) {
      throw new Error(`${inputName} input mode must be 'text' or 'file'`);
    }

    if (input.mode === "text") {
      if (typeof input.text !== "string" || input.text.trim().length === 0) {
        throw new Error(`${inputName} text is required`);
      }
      return;
    }

    if (!input.file || !(input.file instanceof File)) {
      throw new Error(`A valid ${inputName} file is required`);
    }
    if (!CvClient.validateFile(input.file)) {
      throw new Error(`Unsupported ${inputName} file type. Please upload PDF or DOCX files only.`);
    }
  }

  _validateOptionalInput(input, inputName) {
    if (!input || (input.mode !== "text" && input.mode !== "file")) {
      throw new Error(`${inputName} input mode must be 'text' or 'file'`);
    }

    if (input.mode === "text") {
      if (input.text == null) {
        return;
      }
      if (typeof input.text !== "string") {
        throw new Error(`${inputName} text must be a string`);
      }
      return;
    }

    if (input.file == null) {
      return;
    }
    if (!(input.file instanceof File)) {
      throw new Error(`A valid ${inputName} file is required`);
    }
    if (!CvClient.validateFile(input.file)) {
      throw new Error(`Unsupported ${inputName} file type. Please upload PDF or DOCX files only.`);
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
