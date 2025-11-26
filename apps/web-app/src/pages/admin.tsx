import { useState, useEffect } from 'react';
import Head from 'next/head';
import Header from '@/components/Header';

interface UsageStats {
  totalRequests: number;
  totalTokens: number;
  activeTools: string[];
}

export default function Admin() {
  const [stats, setStats] = useState<UsageStats | null>(null);

  useEffect(() => {
    // TODO: Fetch usage stats from API
    setStats({
      totalRequests: 0,
      totalTokens: 0,
      activeTools: [],
    });
  }, []);

  return (
    <>
      <Head>
        <title>Admin - QuantumX AI</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div className="admin-layout">
        <Header onToggleSidebar={() => {}} />
        <main className="admin-content">
          <h1>Administration</h1>
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Requests</h3>
              <p>{stats?.totalRequests || 0}</p>
            </div>
            <div className="stat-card">
              <h3>Total Tokens</h3>
              <p>{stats?.totalTokens || 0}</p>
            </div>
            <div className="stat-card">
              <h3>Active Tools</h3>
              <p>{stats?.activeTools.length || 0}</p>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}

