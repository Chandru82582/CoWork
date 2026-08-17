import { useCallback, useEffect, useState } from "react";
import { fetchCustomers } from "../api/client.js";

const DEFAULT_FILTERS = {
  partner_names: [],
  states: [],
  risk_categories: [],
  tenure_min: undefined,
  tenure_max: undefined,
  salary_min: undefined,
  salary_max: undefined,
  age_min: undefined,
  age_max: undefined,
  search: "",
};

export function useCustomers() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [data, setData] = useState({ meta: null, items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      Object.entries(filters).forEach(([key, val]) => {
        if (val === undefined || val === "" || (Array.isArray(val) && val.length === 0)) return;
        params[key] = val;
      });
      const result = await fetchCustomers(params);
      setData(result);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load customers.");
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);

  useEffect(() => {
    load();
  }, [load]);

  const updateFilters = useCallback((patch) => {
    setPage(1);
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  const resetFilters = useCallback(() => {
    setPage(1);
    setFilters(DEFAULT_FILTERS);
  }, []);

  return { filters, updateFilters, resetFilters, page, setPage, data, loading, error, reload: load };
}
