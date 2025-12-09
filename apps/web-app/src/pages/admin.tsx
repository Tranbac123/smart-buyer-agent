import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import styles from '@/styles/Admin.module.css';

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
      <div className={styles.container}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerContent}>
            <div className={styles.branding}>
              <div className={styles.logo}>
                <span className={styles.logoText}>QX</span>
              </div>
              <div className={styles.brandInfo}>
                <h1>QuantumX AI</h1>
                <p>Administration</p>
              </div>
            </div>
            <Link 
              href="/"
              className="button-secondary"
            >
              Back to Home
            </Link>
          </div>
        </header>

        {/* Main Content */}
        <main className={styles.main}>
          <div className={styles.title}>
            <h2>Dashboard</h2>
            <p>Monitor system performance and usage statistics</p>
          </div>

          {/* Stats Grid */}
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statHeader}>
                <h3 className={styles.statLabel}>Total Requests</h3>
                <svg className={styles.statIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <p className={styles.statValue}>{stats?.totalRequests || 0}</p>
              <p className={styles.statDescription}>All-time requests</p>
            </div>

            <div className={styles.statCard}>
              <div className={styles.statHeader}>
                <h3 className={styles.statLabel}>Total Tokens</h3>
                <svg className={styles.statIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className={styles.statValue}>{stats?.totalTokens.toLocaleString() || 0}</p>
              <p className={styles.statDescription}>Processed tokens</p>
            </div>

            <div className={styles.statCard}>
              <div className={styles.statHeader}>
                <h3 className={styles.statLabel}>Active Tools</h3>
                <svg className={styles.statIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className={styles.statValue}>{stats?.activeTools.length || 0}</p>
              <p className={styles.statDescription}>Registered tools</p>
            </div>
          </div>

          {/* System Status */}
          <div className={styles.systemStatus}>
            <h3>System Status</h3>
            <div className={styles.statusList}>
              <div className={styles.statusItem}>
                <div className={styles.statusLeft}>
                  <div className={styles.statusDot}></div>
                  <span className={styles.statusName}>API Server</span>
                </div>
                <span className={styles.statusBadge}>Operational</span>
              </div>
              <div className={styles.statusItem}>
                <div className={styles.statusLeft}>
                  <div className={styles.statusDot}></div>
                  <span className={styles.statusName}>Smart Buyer Agent</span>
                </div>
                <span className={styles.statusBadge}>Operational</span>
              </div>
              <div className={styles.statusItem}>
                <div className={styles.statusLeft}>
                  <div className={styles.statusDot}></div>
                  <span className={styles.statusName}>Memory Service</span>
                </div>
                <span className={styles.statusBadge}>Operational</span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className={styles.footer}>
            <p>QuantumX AI v0.1.0 • Built with Next.js and FastAPI</p>
          </div>
        </main>
      </div>
    </>
  );
}

