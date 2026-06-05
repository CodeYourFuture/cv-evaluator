/**
 * Main application script for CV Evaluation frontend
 * Handles UI interactions for CV + optional job description evaluation flow
 */

import CvClient from "./cv-client.js";
import {
  checkAuth,
  updateAuthUI,
  checkAuthError,
  initAuthErrorDismiss,
  isAuthenticated,
} from "./auth.js";

// Application state
const cvClient = new CvClient();
let cvMode = "text";
let jdMode = "text";
let isSubmitting = false;

// DOM elements
const cvTextModeBtn = document.getElementById("cvTextModeBtn");
const cvFileModeBtn = document.getElementById("cvFileModeBtn");
const jdTextModeBtn = document.getElementById("jdTextModeBtn");
const jdFileModeBtn = document.getElementById("jdFileModeBtn");
const cvTextSection = document.getElementById("cvTextSection");
const cvFileSection = document.getElementById("cvFileSection");
const jdTextSection = document.getElementById("jdTextSection");
const jdFileSection = document.getElementById("jdFileSection");
const cvTextArea = document.getElementById("cvText");
const jdTextArea = document.getElementById("jdText");
const cvFileInput = document.getElementById("cvFile");
const jdFileInput = document.getElementById("jdFile");
const cvFileRemoveBtn = document.getElementById("cvFileRemoveBtn");
const jdFileRemoveBtn = document.getElementById("jdFileRemoveBtn");
const submitBtn = document.getElementById("submitBtn");
const clearBtn = document.getElementById("clearBtn");
const resultSection = document.getElementById("resultSection");
const resultContent = document.getElementById("resultContent");
const loadingIndicator = document.getElementById("loadingIndicator");
const formActions = document.querySelector(".form-actions");

function switchCvMode(mode) {
  cvMode = mode;
  cvTextModeBtn.classList.toggle("active", mode === "text");
  cvFileModeBtn.classList.toggle("active", mode === "file");
  cvTextSection.style.display = mode === "text" ? "block" : "none";
  cvFileSection.style.display = mode === "file" ? "block" : "none";

  hideResults();
  updateSubmitButton();
}

function switchJdMode(mode) {
  jdMode = mode;
  jdTextModeBtn.classList.toggle("active", mode === "text");
  jdFileModeBtn.classList.toggle("active", mode === "file");
  jdTextSection.style.display = mode === "text" ? "block" : "none";
  jdFileSection.style.display = mode === "file" ? "block" : "none";

  hideResults();
  updateSubmitButton();
}

function handleFileSelection(fileInput, fileInfoId, removeBtnId, inputLabel) {
  const file = fileInput.files[0];
  const fileInfo = document.getElementById(fileInfoId);
  const removeBtn = document.getElementById(removeBtnId);

  if (file) {
    if (!CvClient.validateFile(file)) {
      showError(`Invalid ${inputLabel} file type. Please select a PDF or DOCX file.`);
      fileInput.value = "";
      if (fileInfo) {
        fileInfo.textContent = "";
        fileInfo.style.display = "none";
      }
      if (removeBtn) {
        removeBtn.style.display = "none";
      }
      return;
    }

    if (fileInfo) {
      fileInfo.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
      fileInfo.style.display = "block";
    }
    if (removeBtn) {
      removeBtn.style.display = "inline-flex";
    }
  } else if (fileInfo) {
    fileInfo.textContent = "";
    fileInfo.style.display = "none";
    if (removeBtn) {
      removeBtn.style.display = "none";
    }
  }

  updateSubmitButton();
}

function removeSelectedFile(fileInput, fileInfoId, removeBtnId) {
  fileInput.value = "";
  const fileInfo = document.getElementById(fileInfoId);
  const removeBtn = document.getElementById(removeBtnId);

  if (fileInfo) {
    fileInfo.textContent = "";
    fileInfo.style.display = "none";
  }

  if (removeBtn) {
    removeBtn.style.display = "none";
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
    submitBtn.textContent = "Evaluate";
  }
}

function canSubmitForm() {
  return getCvInput() !== null;
}

function getCvInput() {
  if (cvMode === "text") {
    const text = cvTextArea.value.trim();
    if (!text) {
      return null;
    }
    return { mode: "text", text };
  }

  const file = cvFileInput.files[0];
  if (!file) {
    return null;
  }
  return { mode: "file", file };
}

function getJdInput() {
  if (jdMode === "text") {
    const text = jdTextArea.value.trim();
    return text ? { mode: "text", text } : null;
  }

  const file = jdFileInput.files[0];
  return file ? { mode: "file", file } : null;
}

async function handleSubmit() {
  if (!canSubmitForm() || isSubmitting) {
    return;
  }

  // Check auth before submitting
  if (!isAuthenticated()) {
    showError("You must be logged in to evaluate CVs. Please sign in with GitHub.");
    return;
  }

  isSubmitting = true;
  updateSubmitButton();
  showLoading();
  hideResults();

  try {
    const cvInput = getCvInput();
    const jdInput = getJdInput();
    const result = await cvClient.evaluateSubmission({
      cv: cvInput,
      jd: jdInput,
    });

    showSuccess(result);
  } catch (error) {
    // Handle 401 errors specially
    if (error.message.includes("401") || error.message.toLowerCase().includes("authentication")) {
      showError("Your session has expired. Please sign in again.");
      // Re-check auth state to update UI
      const user = await checkAuth();
      updateAuthUI(user);
    } else {
      showError(error.message);
    }
  } finally {
    isSubmitting = false;
    updateSubmitButton();
    hideLoading();
  }
}

function clearForm() {
  cvTextArea.value = "";
  jdTextArea.value = "";

  cvFileInput.value = "";
  jdFileInput.value = "";

  const cvFileInfo = document.getElementById("cvFileInfo");
  const jdFileInfo = document.getElementById("jdFileInfo");
  if (cvFileInfo) {
    cvFileInfo.textContent = "";
    cvFileInfo.style.display = "none";
  }
  if (jdFileInfo) {
    jdFileInfo.textContent = "";
    jdFileInfo.style.display = "none";
  }
  if (cvFileRemoveBtn) {
    cvFileRemoveBtn.style.display = "none";
  }
  if (jdFileRemoveBtn) {
    jdFileRemoveBtn.style.display = "none";
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

  const categoryLabels = {
    spelling_grammar: "Spelling & Grammar",
    two_pages: "Two Pages",
    contact_details: "Contact Details",
    dates: "Dates",
    pronouns: "No Personal Pronouns",
    tense: "Tense",
    buzzwords: "No Buzzwords",
    summary: "Summary",
    outcomes: "Outcomes",
    project: "Projects",
    experience: "Experience",
    education: "Education",
  };

  const jdCategoryLabels = {
    jd_match_for_computers: "JD Match For Computers (ATS)",
    jd_match_for_people: "JD Match For People",
  };

  let coreEvaluationListHtml = "";
  for (const [key, label] of Object.entries(categoryLabels)) {
    if (result[key]) {
      const ruleResult = result[key];
      const passed = ruleResult.passed;
      const icon = passed ? "✓" : "✗";
      const iconClass = passed ? "icon-pass" : "icon-fail";

      coreEvaluationListHtml += `
                <li class="evaluation-item ${passed ? "passed" : "failed"}">
                    <span class="evaluation-icon ${iconClass}">${icon}</span>
                    <span class="evaluation-category">${label}</span>
                    <span class="evaluation-details">${escapeHtml(ruleResult.details)}</span>
                </li>
            `;
    }
  }

  let jdEvaluationListHtml = "";
  for (const [key, label] of Object.entries(jdCategoryLabels)) {
    if (result[key]) {
      const ruleResult = result[key];
      const passed = ruleResult.passed;
      const icon = passed ? "✓" : "✗";
      const iconClass = passed ? "icon-pass" : "icon-fail";

      jdEvaluationListHtml += `
                <li class="evaluation-item ${passed ? "passed" : "failed"}">
                    <span class="evaluation-icon ${iconClass}">${icon}</span>
                    <span class="evaluation-category">${label}</span>
                    <span class="evaluation-details">${escapeHtml(ruleResult.details)}</span>
                </li>
            `;
    }
  }

  const jdSectionHtml = jdEvaluationListHtml
    ? `
        <h3 class="evaluation-subheading">Job Description Match</h3>
        <ul class="evaluation-list">
            ${jdEvaluationListHtml}
        </ul>
      `
    : "";

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
        <h3 class="evaluation-subheading">Core CV Rules</h3>
        <ul class="evaluation-list">
          ${coreEvaluationListHtml}
        </ul>
        ${jdSectionHtml}
        ${result.debug_info ? `<div class="debug-info"><strong>Debug Info:</strong> ${escapeHtml(result.debug_info)}</div>` : ""}
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
cvTextModeBtn.addEventListener("click", () => switchCvMode("text"));
cvFileModeBtn.addEventListener("click", () => switchCvMode("file"));
jdTextModeBtn.addEventListener("click", () => switchJdMode("text"));
jdFileModeBtn.addEventListener("click", () => switchJdMode("file"));
submitBtn.addEventListener("click", handleSubmit);
clearBtn.addEventListener("click", clearForm);
cvFileInput.addEventListener("change", () => handleFileSelection(cvFileInput, "cvFileInfo", "cvFileRemoveBtn", "CV"));
jdFileInput.addEventListener("change", () => handleFileSelection(jdFileInput, "jdFileInfo", "jdFileRemoveBtn", "job description"));
if (cvFileRemoveBtn) {
  cvFileRemoveBtn.addEventListener("click", () => removeSelectedFile(cvFileInput, "cvFileInfo", "cvFileRemoveBtn"));
}
if (jdFileRemoveBtn) {
  jdFileRemoveBtn.addEventListener("click", () => removeSelectedFile(jdFileInput, "jdFileInfo", "jdFileRemoveBtn"));
}
cvTextArea.addEventListener("input", updateSubmitButton);
jdTextArea.addEventListener("input", updateSubmitButton);

// Ctrl+Enter to submit
cvTextArea.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") {
    handleSubmit();
  }
});

// Initialize authentication and UI
async function initApp() {
  // Check for OAuth errors in URL
  checkAuthError();
  initAuthErrorDismiss();

  // Check authentication status
  const user = await checkAuth();
  updateAuthUI(user);

  switchCvMode("text");
  switchJdMode("text");
}

// Start the app
initApp();
