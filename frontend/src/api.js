// All API calls live here: one function per endpoint (Section 13.4).
import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({ baseURL: `${API_BASE_URL}/api` });

/** Turn any axios error into { code, message } using the server's error shape. */
export function toApiError(err) {
  if (err.response?.data?.error) return err.response.data.error;
  if (err.request) return { code: 'network_error', message: "Can't reach the server." };
  return { code: 'unknown_error', message: 'Something went wrong.' };
}

export async function getHealth() {
  const { data } = await client.get('/health');
  return data;
}
