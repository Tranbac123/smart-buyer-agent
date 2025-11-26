/**
 * Sidebar Component
 * Contains New Chat button and Chat List
 */

import NewChatButton from "./NewChatButton";
import ChatList from "./ChatList";

export default function Sidebar() {
  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">QX</span>
          </div>
          <div>
            <h1 className="font-bold text-lg">QuantumX AI</h1>
            <p className="text-xs text-gray-500">Smart AI Assistant</p>
          </div>
        </div>
        
        <NewChatButton />
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto p-3">
        <ChatList />
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>All systems operational</span>
          </div>
          <div>Version 0.1.0</div>
        </div>
      </div>
    </div>
  );
}
