// Centralized backend API configuration.
// In production this defaults to the deployed Render backend; override via VITE_API_BASE if needed.
const PROD_BASE = 'https://nbfc-inc.onrender.com';

export const API_BASE =
  (import.meta.env.VITE_API_BASE as string) ||
  (import.meta.env.PROD ? PROD_BASE : 'http://localhost:8000');
