// MS Softwares - Authentication with 30-minute session expiry
const ADMIN_PASSWORD = 'mssoftware@sai9361802547';
const SESSION_DURATION = 30 * 60 * 1000; // 30 minutes in milliseconds

export const login = (password) => {
  if (password === ADMIN_PASSWORD) {
    const loginTime = Date.now();
    const expiryTime = loginTime + SESSION_DURATION;

    const token = btoa(`admin:${loginTime}`);
    localStorage.setItem('token', token);
    localStorage.setItem('isAuthenticated', 'true');
    localStorage.setItem('loginTime', loginTime.toString());
    localStorage.setItem('expiryTime', expiryTime.toString());

    return true;
  }
  return false;
};

export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('isAuthenticated');
  localStorage.removeItem('loginTime');
  localStorage.removeItem('expiryTime');
};

export const isAuthenticated = () => {
  const isAuth = localStorage.getItem('isAuthenticated') === 'true';
  const expiryTime = parseInt(localStorage.getItem('expiryTime') || '0');
  const currentTime = Date.now();

  // Check if session is expired
  if (isAuth && expiryTime > 0 && currentTime > expiryTime) {
    // Session expired - auto logout
    logout();
    return false;
  }

  return isAuth;
};

export const getRemainingTime = () => {
  const expiryTime = parseInt(localStorage.getItem('expiryTime') || '0');
  const currentTime = Date.now();
  const remaining = expiryTime - currentTime;

  if (remaining <= 0) return 0;

  return Math.floor(remaining / 1000); // Return seconds
};

export const getPasswordHint = () => {
  // Don't show the actual password - just a hint
  return 'Contact administrator for password';
};
