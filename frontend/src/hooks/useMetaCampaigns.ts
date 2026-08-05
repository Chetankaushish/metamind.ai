import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

export function useMetaCampaigns() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getCampaigns();
      setCampaigns(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch Meta campaigns');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  return { campaigns, loading, error, refetch: fetchCampaigns };
}
