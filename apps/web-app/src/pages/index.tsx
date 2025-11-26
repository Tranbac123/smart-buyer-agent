/**
 * Home Page
 * Landing page with option to start new chat
 */

import { useRouter } from "next/router";
import { useChatHistory } from "@/hooks/useChatHistory";

export default function Home() {
  const router = useRouter();
  const { createNew } = useChatHistory();

  const handleStartChat = () => {
    const session = createNew();
    router.push(`/chat/${session.id}`);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-4">
      <div className="max-w-4xl w-full text-center space-y-8">
        {/* Logo */}
        <div className="flex justify-center">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center shadow-xl">
            <span className="text-white font-bold text-4xl">QX</span>
          </div>
        </div>

        {/* Hero */}
        <div className="space-y-4">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900">
            Welcome to{" "}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              QuantumX AI
            </span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Your intelligent AI assistant for shopping, research, and more.
            Powered by advanced agent architecture.
          </p>
        </div>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={handleStartChat}
            className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95"
          >
            Start Chatting
          </button>
          <button
            onClick={() => router.push("/admin")}
            className="px-8 py-4 bg-white text-gray-700 rounded-xl font-semibold text-lg border-2 border-gray-200 hover:border-gray-300 transition-all hover:scale-105 active:scale-95"
          >
            Admin Panel
          </button>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-4xl mx-auto">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="text-4xl mb-4">🛍️</div>
            <h3 className="text-lg font-semibold mb-2">Smart Shopping</h3>
            <p className="text-gray-600 text-sm">
              Compare prices across Shopee, Lazada, and Tiki. Get intelligent
              recommendations based on price, ratings, and reviews.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="text-4xl mb-4">🔬</div>
            <h3 className="text-lg font-semibold mb-2">Deep Research</h3>
            <p className="text-gray-600 text-sm">
              In-depth analysis with multi-step reasoning. Get comprehensive
              answers with proper citations and fact-checking.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="text-4xl mb-4">💬</div>
            <h3 className="text-lg font-semibold mb-2">Natural Chat</h3>
            <p className="text-gray-600 text-sm">
              Conversational AI for quick questions and friendly interactions.
              Fast responses with context awareness.
            </p>
          </div>
        </div>

        {/* Tech Stack */}
        <div className="pt-16 text-sm text-gray-500 space-y-2">
          <div>Built with Next.js, React, TypeScript, and FastAPI</div>
          <div>
            Powered by agent_core architecture with Plan → Act → Observe →
            Reflect → Refine loop
          </div>
        </div>
      </div>
    </div>
  );
}
