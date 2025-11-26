import { useState } from 'react';
import Head from 'next/head';
import ChatWindow from '@/components/ChatWindow';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import { useChat } from '@/hooks/useChat';

export default function Chat() {
  const { messages, sessions, currentSession, sendMessage, createNewSession, selectSession } = useChat();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <>
      <Head>
        <title>Chat - QuantumX AI</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div className="chat-layout">
        <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <div className="chat-container">
          {sidebarOpen && (
            <Sidebar
              sessions={sessions}
              currentSession={currentSession}
              onSelectSession={selectSession}
              onNewSession={createNewSession}
            />
          )}
          <ChatWindow
            messages={messages}
            onSendMessage={sendMessage}
            isLoading={false}
          />
        </div>
      </div>
    </>
  );
}

