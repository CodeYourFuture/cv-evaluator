/**
 * Authentication module for CV Evaluation frontend
 * Handles checking auth state and updating UI
 */

/**
 * Current user data (null if not authenticated)
 * @type {Object|null}
 */
let currentUser = null;

/**
 * Check authentication status by calling /api/auth/me
 * @returns {Promise<Object|null>} User object if authenticated, null otherwise
 */
export async function checkAuth() {
  try {
    const response = await fetch("/api/auth/me", {
      credentials: "include", // Include cookies
    });

    if (response.ok) {
      currentUser = await response.json();
      return currentUser;
    }

    currentUser = null;
    return null;
  } catch (error) {
    console.error("Auth check failed:", error);
    currentUser = null;
    return null;
  }
}

/**
 * Get the current user (from memory, does not make API call)
 * @returns {Object|null} Current user or null
 */
export function getCurrentUser() {
  return currentUser;
}

/**
 * Check if user is authenticated
 * @returns {boolean}
 */
export function isAuthenticated() {
  return currentUser !== null;
}

/**
 * Redirect to login page
 */
export function login() {
  window.location.href = "/api/auth/login";
}

/**
 * Redirect to logout endpoint
 */
export function logout() {
  window.location.href = "/api/auth/logout";
}

/**
 * Update UI based on authentication state
 * @param {Object|null} user - Current user or null
 */
export function updateAuthUI(user) {
  const authLoading = document.getElementById("authLoading");
  const loggedOut = document.getElementById("loggedOut");
  const loggedIn = document.getElementById("loggedIn");
  const loginRequired = document.getElementById("loginRequired");
  const mainContent = document.getElementById("mainContent");
  const userAvatar = document.getElementById("userAvatar");
  const userName = document.getElementById("userName");

  // Hide loading state
  if (authLoading) authLoading.style.display = "none";

  if (user) {
    // User is logged in
    if (loggedOut) loggedOut.style.display = "none";
    if (loggedIn) loggedIn.style.display = "flex";
    if (loginRequired) loginRequired.style.display = "none";
    if (mainContent) mainContent.style.display = "block";

    // Update user info
    if (userAvatar) {
      userAvatar.src = user.avatar_url;
      userAvatar.alt = `${user.name}'s avatar`;
    }
    if (userName) userName.textContent = user.name || user.username;
  } else {
    // User is not logged in
    if (loggedOut) loggedOut.style.display = "block";
    if (loggedIn) loggedIn.style.display = "none";
    if (loginRequired) loginRequired.style.display = "block";
    if (mainContent) mainContent.style.display = "none";
  }
}

/**
 * Check for OAuth error in URL and display it
 * @returns {string|null} Error message if present
 */
export function checkAuthError() {
  const urlParams = new URLSearchParams(window.location.search);
  const error = urlParams.get("error");

  if (error) {
    const authError = document.getElementById("authError");
    const authErrorMessage = document.getElementById("authErrorMessage");

    if (authError && authErrorMessage) {
      authErrorMessage.textContent = error;
      authError.style.display = "block";
    }

    // Clean URL without reloading
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl);

    return error;
  }

  return null;
}

/**
 * Initialize auth error dismiss button
 */
export function initAuthErrorDismiss() {
  const dismissBtn = document.getElementById("dismissError");
  const authError = document.getElementById("authError");

  if (dismissBtn && authError) {
    dismissBtn.addEventListener("click", () => {
      authError.style.display = "none";
    });
  }
}
