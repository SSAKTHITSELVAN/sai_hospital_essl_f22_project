// Simple static password authentication
const ADMIN_PASSWORD = 'admin123'; // Change this to your password

export const login = (password) => {
  if (password === ADMIN_PASSWORD) {
    const token = btoa(`admin:${Date.now()}`); // Simple token
    localStorage.setItem('token', token);
    localStorage.setItem('isAuthenticated', 'true');
    return true;
  }
  return false;
};

export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('isAuthenticated');
};

export const isAuthenticated = () => {
  return localStorage.getItem('isAuthenticated') === 'true';
};