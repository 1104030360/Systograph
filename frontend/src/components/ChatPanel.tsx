import { Bot, Cpu, MessageCircle, SendHorizontal } from "lucide-react";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function ChatPanel({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <>
      <div className="drawer-scrim" role="presentation" onClick={onClose} />
      <aside className="chat-drawer" aria-label="Local model chat">
        <div className="chat-head">
          <div>
            <h3>Local model</h3>
            <p>Reserved for local model conversations grounded in the system map.</p>
          </div>
          <span className="chat-standby">
            <Cpu size={12} />
            standby
          </span>
        </div>

        <div className="chat-body">
          <div className="chat-msg">
            <span className="ico">
              <Bot size={15} />
            </span>
            <span>When the backend exposes model chat, the selected node and scan context can be sent here.</span>
          </div>
          <div className="chat-msg">
            <span className="ico">
              <MessageCircle size={15} />
            </span>
            <span>You'll be able to ask why a node was detected, which files support it, or what to inspect next.</span>
          </div>
        </div>

        <form className="chat-composer" onSubmit={(event) => event.preventDefault()}>
          <input aria-label="Local model chat input" disabled placeholder="Waiting for local model API" />
          <button className="icon-btn" type="button" disabled aria-label="Send message">
            <SendHorizontal size={15} />
          </button>
        </form>
      </aside>
    </>
  );
}
