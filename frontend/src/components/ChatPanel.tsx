import { Bot, Cpu, MessageCircle, SendHorizontal } from "lucide-react";

export function ChatPanel() {
  return (
    <aside className="chat-panel">
      <div className="chat-header">
        <div>
          <span className="section-label">Local Model</span>
          <h2>Chat</h2>
          <p>Reserved for local model conversations.</p>
        </div>
        <span className="chat-status">
          <Cpu size={14} />
          Standby
        </span>
      </div>

      <div className="chat-thread">
        <div className="chat-message assistant">
          <Bot size={16} />
          <p>When the backend exposes model chat, selected nodes and scan context can be sent here.</p>
        </div>
        <div className="chat-message assistant">
          <MessageCircle size={16} />
          <p>For example, you will be able to ask why a node was detected, which files support it, or what to inspect next.</p>
        </div>
      </div>

      <form className="chat-composer">
        <input aria-label="Local model chat input" disabled placeholder="Waiting for local model API" />
        <button aria-label="Send message" disabled type="button">
          <SendHorizontal size={16} />
        </button>
      </form>
    </aside>
  );
}
