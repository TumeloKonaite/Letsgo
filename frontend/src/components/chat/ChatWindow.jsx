// Render the chat panel and coordinate focus, scrolling, and conversation controls.

import { useEffect, useRef } from "react";

import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";

export function ChatWindow({
  inputValue,
  isOpen,
  isSending,
  messages,
  onClose,
  onInputChange,
  onStarterPrompt,
  onSubmit,
  starterPrompts,
}) {
  const scrollAnchorRef = useRef(null);
  const showStarterPrompts = !messages.some((message) => message.role === "user");

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    scrollAnchorRef.current?.scrollIntoView({ block: "end" });
  }, [isOpen, isSending, messages]);

  if (!isOpen) {
    return null;
  }

  return (
    <>
      <button
        className="chat-widget__backdrop"
        type="button"
        aria-label="Close travel assistant"
        onClick={onClose}
      />

      <section
        id="travel-assistant-panel"
        className="chat-window fade-up"
        role="dialog"
        aria-modal="false"
        aria-labelledby="travel-assistant-title"
      >
        <header className="chat-window__header">
          <div>
            <p className="chat-window__eyebrow">AI Travel Assistant</p>
            <h2 id="travel-assistant-title">Plan your trip with LetsGoSA</h2>
          </div>
          <button
            className="chat-window__close"
            type="button"
            aria-label="Minimize chat"
            onClick={onClose}
          >
            <span aria-hidden="true">x</span>
          </button>
        </header>

        <div
          className="chat-window__messages"
          role="log"
          aria-live="polite"
          aria-relevant="additions text"
        >
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {isSending ? (
            <ChatMessage
              message={{
                id: "typing-indicator",
                role: "assistant",
                content: "",
                createdAt: new Date().toISOString(),
                isTyping: true,
              }}
            />
          ) : null}

          <div ref={scrollAnchorRef} />
        </div>

        {showStarterPrompts ? (
          <div className="chat-window__prompts" aria-label="Suggested questions">
            {starterPrompts.map((prompt) => (
              <button
                key={prompt}
                className="chat-window__prompt"
                type="button"
                onClick={() => onStarterPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}

        <ChatInput
          disabled={isSending}
          onChange={onInputChange}
          onSubmit={onSubmit}
          shouldFocus={isOpen}
          value={inputValue}
        />
      </section>
    </>
  );
}
