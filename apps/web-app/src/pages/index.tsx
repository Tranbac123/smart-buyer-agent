/**
 * Home Page
 * Landing page with option to start new chat
 */

import { useRouter } from "next/router";
import { useChatHistory } from "@/hooks/useChatHistory";
import styles from "@/styles/Landing.module.css";

export default function Home() {
  const router = useRouter();
  const { createNew } = useChatHistory();

  const handleStartChat = () => {
    const session = createNew();
    router.push(`/chat/${session.id}`);
  };

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        {/* Logo */}
        <div className={styles.logo}>
          <span className={styles.logoText}>QX</span>
        </div>

        {/* Hero */}
        <div className={styles.hero}>
          <h1 className={styles.title}>
            Welcome to{" "}
            <span className={styles.titleAccent}>QuantumX AI</span>
          </h1>
          <p className={styles.subtitle}>
            Ask anything – I can help with shopping, research, and more!
            Powered by advanced agent architecture.
          </p>
        </div>

        {/* CTA */}
        <div className={styles.ctaButtons}>
          <button
            onClick={handleStartChat}
            className="button-primary"
          >
            Start Chatting
          </button>
          <button
            onClick={() => router.push("/admin")}
            className="button-secondary"
          >
            Admin Panel
          </button>
        </div>

        {/* Features */}
        <div className={styles.features}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>🛍️</div>
            <h3 className={styles.featureTitle}>Smart Shopping</h3>
            <p className={styles.featureDescription}>
              Compare prices across Shopee, Lazada, and Tiki. Get intelligent
              recommendations based on price, ratings, and reviews.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>🔬</div>
            <h3 className={styles.featureTitle}>Deep Research</h3>
            <p className={styles.featureDescription}>
              In-depth analysis with multi-step reasoning. Get comprehensive
              answers with proper citations and fact-checking.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>💬</div>
            <h3 className={styles.featureTitle}>Natural Chat</h3>
            <p className={styles.featureDescription}>
              Conversational AI for quick questions and friendly interactions.
              Fast responses with context awareness.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <p className={styles.footerText}>Built with Next.js, React, TypeScript, and FastAPI</p>
          <p className={styles.footerText}>
            Powered by agent_core architecture with Plan → Act → Observe →
            Reflect → Refine loop
          </p>
        </div>
      </div>
    </div>
  );
}
