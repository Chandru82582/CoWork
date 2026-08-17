import { useCallback, useEffect, useState } from "react";
// import {
//   fetchKpis, fetchChurnByPartner, fetchChurnByState, fetchChurnByAgeBracket,
//   fetchRiskTierSplit, fetchVolumeTreemap, fetchRegistrationHeatmap,
// } from "../api/client.js";

import {
  fetchKpis, fetchChurnByPartner, fetchChurnByAgeBracket,fetchChurnByState,
  fetchRiskTierSplit, 
} from "../api/client.js";

// const initial = {
//   kpis: null,
//   churnByPartner: [],
//   churnByState: [],
//   churnByAgeBracket: [],
//   riskTierSplit: [],
//   volumeTreemap: [],
//   registrationHeatmap: null,
// };

const initial = {
  kpis: null,
  churnByPartner: [],
  churnByAgeBracket: [],
  churnByState: [],
  riskTierSplit: [],
};

export function useAnalytics() {
  const [data, setData] = useState(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    // try {
    //   const [kpis, churnByPartner, churnByState, churnByAgeBracket, riskTierSplit, volumeTreemap, registrationHeatmap] =
    //     await Promise.all([
    //       fetchKpis(), fetchChurnByPartner(), fetchChurnByState(), fetchChurnByAgeBracket(),
    //       fetchRiskTierSplit(), fetchVolumeTreemap(), fetchRegistrationHeatmap(120),
    //     ]);
    //   setData({ kpis, churnByPartner, churnByState, churnByAgeBracket, riskTierSplit, volumeTreemap, registrationHeatmap });
    // }
    try {
      const [kpis, churnByPartner, churnByState,churnByAgeBracket, riskTierSplit] =
        await Promise.all([
          fetchKpis(), fetchChurnByPartner(),fetchChurnByState(), fetchChurnByAgeBracket(),
          fetchRiskTierSplit(),
        ]);
        setData({ kpis, churnByPartner,  churnByAgeBracket,churnByState, riskTierSplit });

    }catch (e) {
      setError(e?.response?.data?.detail || "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { ...data, loading, error, reload: load };
}
