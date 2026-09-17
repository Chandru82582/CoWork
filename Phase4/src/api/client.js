import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({ baseURL: BASE_URL });

let onUnauthorized = () => {};
export function registerUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("signal_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401) onUnauthorized();
    return Promise.reject(error);
  }
);

// ---- Auth ----
export async function login(username, password) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const res = await apiClient.post("/token", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data; // { access_token, token_type }
}

// ---- Dashboard ----
export const fetchKpis = () => apiClient.get("/dashboard/kpis").then((r) => r.data);

export const fetchCustomers = (params) =>
  apiClient
    .get("/dashboard/customers", { params, paramsSerializer: { indexes: null } })
    .then((r) => r.data);

export const fetchCustomerDetail = (customerId) =>
  apiClient.get(`/dashboard/customers/${customerId}/detail`).then((r) => r.data);

export const fetchChurnByPartner = () =>
  apiClient.get("/dashboard/analytics/churn-by-partner").then((r) => r.data);

export const fetchChurnByState = () =>
  apiClient.get("/dashboard/analytics/churn-by-state").then((r) => r.data);

export const fetchChurnByAgeBracket = () =>
  apiClient.get("/dashboard/analytics/churn-by-age-bracket").then((r) => r.data);

export const fetchRiskTierSplit = () =>
  apiClient.get("/dashboard/analytics/risk-tier-split").then((r) => r.data);

// export const fetchVolumeTreemap = () =>
//   apiClient.get("/dashboard/analytics/volume-treemap").then((r) => r.data);

// export const fetchRegistrationHeatmap = (days = 120) =>
//   apiClient
//     .get("/dashboard/analytics/registration-heatmap", { params: { days } })
//     .then((r) => r.data);

// ---- ML prediction ----
export const predictChurn = (payload) =>
  apiClient.post("/ml/predict-churn", payload).then((r) => r.data);

// ---- AI Assistant ----
export const sendAssistantChat = (messages) =>
  apiClient.post("/assistant/chat", { messages }).then((r) => r.data);
