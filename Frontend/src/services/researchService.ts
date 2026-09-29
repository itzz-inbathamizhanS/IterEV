const API_BASE =
  (import.meta as unknown as { env: Record<string, string> }).env?.["VITE_API_URL"] ??
  "http://localhost:8000";

export type ResearchResult<T> = {
  data: T[];
  metadata: {
    source: string;
    scenario?: string;
  };
};

export const researchService = {
  async getBaseline(scenario: string): Promise<ResearchResult<unknown>> {
    const res = await fetch(
      `${API_BASE}/api/research/baseline?scenario=${encodeURIComponent(scenario)}`,
    );
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getAblation(scenario: string): Promise<ResearchResult<unknown>> {
    const res = await fetch(
      `${API_BASE}/api/research/ablation?scenario=${encodeURIComponent(scenario)}`,
    );
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getReplication(): Promise<ResearchResult<unknown>> {
    const res = await fetch(`${API_BASE}/api/research/replication`);
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getMonotonicity(): Promise<ResearchResult<unknown>> {
    const res = await fetch(`${API_BASE}/api/research/monotonicity`);
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getConvergence(): Promise<ResearchResult<unknown>> {
    const res = await fetch(`${API_BASE}/api/research/convergence`);
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getSensitivity(parameter: string): Promise<ResearchResult<unknown>> {
    const res = await fetch(
      `${API_BASE}/api/research/sensitivity?parameter=${encodeURIComponent(parameter)}`,
    );
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getRiskDecomposition(): Promise<ResearchResult<unknown>> {
    const res = await fetch(`${API_BASE}/api/research/risk-decomposition`);
    if (!res.ok) throw new Error("RESULT NOT GENERATED");
    return res.json();
  },

  async getFailureTaxonomy(): Promise<ResearchResult<unknown>> {
    const res = await fetch(`${API_BASE}/api/research/failure-taxonomy`);
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getTrajectories(): Promise<ResearchResult<unknown>> {
    const res = await fetch(`${API_BASE}/api/research/trajectories`);
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },

  async getManifest(): Promise<ResearchResult<unknown>> {
    const res = await fetch(`${API_BASE}/api/research/manifest`);
    if (!res.ok) throw new Error("Backend result could not be retrieved.");
    return res.json();
  },
};
