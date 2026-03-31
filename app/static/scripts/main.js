/**
 * Main application script for CV Evaluation frontend
 * Handles UI interactions and CV evaluation flow
 */

import CvClient from "./cv-client.js";

// Application state
const cvClient = new CvClient();
let currentMode = "text";
let isSubmitting = false;

// DOM elements
const textModeBtn = document.getElementById("textModeBtn");
const fileModeBtn = document.getElementById("fileModeBtn");
const textSection = document.getElementById("textSection");
const fileSection = document.getElementById("fileSection");
const cvTextArea = document.getElementById("cvText");
const fileInput = document.getElementById("cvFile");
const submitBtn = document.getElementById("submitBtn");
const clearBtn = document.getElementById("clearBtn");
const resultSection = document.getElementById("resultSection");
const resultContent = document.getElementById("resultContent");
const loadingIndicator = document.getElementById("loadingIndicator");
const formActions = document.querySelector(".form-actions");

function switchMode(mode) {
  currentMode = mode;

  // Update button states
  textModeBtn.classList.toggle("active", mode === "text");
  fileModeBtn.classList.toggle("active", mode === "file");

  // Show/hide sections
  textSection.style.display = mode === "text" ? "block" : "none";
  fileSection.style.display = mode === "file" ? "block" : "none";

  // Clear results and update submit button
  hideResults();
  updateSubmitButton();
}

function handleFileSelection() {
  const file = fileInput.files[0];

  if (file) {
    // Validate file type
    if (!CvClient.validateFile(file)) {
      showError("Invalid file type. Please select a PDF or DOCX file.");
      fileInput.value = "";
      return;
    }

    // Show file info
    const fileInfo = document.getElementById("fileInfo");
    if (fileInfo) {
      fileInfo.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
      fileInfo.style.display = "block";
    }
  }

  updateSubmitButton();
}

function updateSubmitButton() {
  const canSubmit = canSubmitForm();
  submitBtn.disabled = !canSubmit || isSubmitting;

  // Show/hide form actions based on whether there's input
  formActions.classList.toggle("visible", canSubmit);

  if (isSubmitting) {
    submitBtn.textContent = "Evaluating...";
  } else {
    submitBtn.textContent = "Evaluate CV";
  }
}

function canSubmitForm() {
  if (currentMode === "text") {
    return cvTextArea.value.trim().length > 0;
  } else {
    return fileInput.files.length > 0;
  }
}

async function handleSubmit() {
  if (!canSubmitForm() || isSubmitting) {
    return;
  }

  isSubmitting = true;
  updateSubmitButton();
  showLoading();
  hideResults();

  try {
    let result;

    if (currentMode === "text") {
      const text = cvTextArea.value.trim();
      result = await cvClient.evaluateText(text);
    } else {
      const file = fileInput.files[0];
      result = await cvClient.evaluateFile(file);
    }

    showSuccess(result);
  } catch (error) {
    showError(error.message);
  } finally {
    isSubmitting = false;
    updateSubmitButton();
    hideLoading();
  }
}

function clearForm() {
  if (currentMode === "text") {
    cvTextArea.value = "";
  } else {
    fileInput.value = "";
    const fileInfo = document.getElementById("fileInfo");
    if (fileInfo) {
      fileInfo.style.display = "none";
    }
  }

  hideResults();
  updateSubmitButton();
}

function showLoading() {
  loadingIndicator.style.display = "block";
}

function hideLoading() {
  loadingIndicator.style.display = "none";
}

function showSuccess(result) {
  resultSection.className = "result";
  resultSection.style.display = "block";

  // Category labels mapping
  const categoryLabels = {
    spelling_grammar: "Spelling & Grammar",
    two_pages: "Two Pages",
    contact_details: "Contact Details",
    links: "Links",
    dates: "Dates",
    pronouns: "No Personal Pronouns",
    tense: "Tense",
    buzzwords: "No Buzzwords",
    outcomes: "Outcomes",
    project: "Projects",
    experience: "Experience",
  };

  // Build the evaluation list HTML
  let evaluationListHtml = "";
  for (const [key, label] of Object.entries(categoryLabels)) {
    if (result[key]) {
      const ruleResult = result[key];
      const passed = ruleResult.passed;
      const icon = passed ? "✓" : "✗";
      const iconClass = passed ? "icon-pass" : "icon-fail";

      evaluationListHtml += `
                <li class="evaluation-item ${passed ? "passed" : "failed"}">
                    <span class="evaluation-icon ${iconClass}">${icon}</span>
                    <span class="evaluation-category">${label}</span>
                    <span class="evaluation-details">${escapeHtml(ruleResult.details)}</span>
                </li>
            `;
    }
  }

  // Overall status
  const overallPassed = result.passed === true || result.passed === "true";
  const overallIcon = overallPassed ? "✓" : "✗";
  const overallClass = overallPassed ? "overall-pass" : "overall-fail";

  // Format the result
  resultContent.innerHTML = `
        <div class="overall-status ${overallClass}">
            <span class="overall-icon">${overallIcon}</span>
            <span class="overall-text">${overallPassed ? "CV PASSED" : "CV NEEDS IMPROVEMENT"}</span>
        </div>
        <ul class="evaluation-list">
            ${evaluationListHtml}
        </ul>
        ${result.debug_info ? `<div class="debug-info"><strong>Debug Info:</strong> ${escapeHtml(result.debug_info)}</div>` : ""}
        <details class="raw-result">
            <summary>Raw API Response</summary>
            <pre>${JSON.stringify(result, null, 2)}</pre>
        </details>
    `;
}

function showError(message) {
  resultSection.className = "result error";
  resultSection.style.display = "block";

  resultContent.innerHTML = `
        <h4>Error</h4>
        <p>${escapeHtml(message)}</p>
    `;
}

function hideResults() {
  resultSection.style.display = "none";
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

// Event listeners
textModeBtn.addEventListener("click", () => switchMode("text"));
fileModeBtn.addEventListener("click", () => switchMode("file"));
submitBtn.addEventListener("click", handleSubmit);
clearBtn.addEventListener("click", clearForm);
fileInput.addEventListener("change", handleFileSelection);
cvTextArea.addEventListener("input", updateSubmitButton);

// Ctrl+Enter to submit
cvTextArea.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") {
    handleSubmit();
  }
});

// Initialize
switchMode("text");
