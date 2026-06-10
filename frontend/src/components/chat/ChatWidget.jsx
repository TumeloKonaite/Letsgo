import { useEffect, useRef, useState } from "react";

import { submitChatMessage } from "../../lib/api";
import { ChatWindow } from "./ChatWindow";
import "./chat.css";

const CHAT_STORAGE_KEY = "letsgosa-chat-state-v1";
const CHAT_TIMEOUT_MS = 20000;
const STARTER_PROMPTS = [
  "What packages do you offer?",
  "Recommend a weekend getaway.",
  "How do I book a trip?",
  "What destinations are available?",
];

function createMessage(role, content, options = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    createdAt: new Date().toISOString(),
    ...options,
  };
}

function createWelcomeMessage() {
  return createMessage(
    "assistant",
    "Hello. I can help you compare packages, explain pricing, suggest destinations, and share booking details."
  );
}

function loadStoredChatState() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const rawState = window.localStorage.getItem(CHAT_STORAGE_KEY);
    if (!rawState) {
      return null;
    }

    const parsedState = JSON.parse(rawState);
    if (!Array.isArray(parsedState?.messages)) {
      return null;
    }

    return {
      messages: parsedState.messages,
      sessionId: typeof parsedState.sessionId === "string" ? parsedState.sessionId : null,
      unreadCount:
        typeof parsedState.unreadCount === "number" && parsedState.unreadCount >= 0
          ? parsedState.unreadCount
          : 0,
    };
  } catch {
    return null;
  }
}

function buildErrorMessage(error) {
  if (error?.name === "AbortError") {
    return "Sorry, I'm having trouble connecting right now.\nPlease try again in a moment.";
  }

  if (error?.status === 503) {
    return "Sorry, the travel assistant is unavailable right now.\nPlease try again in a moment.";
  }

  if (error instanceof TypeError) {
    return "Sorry, I'm having trouble connecting right now.\nPlease try again in a moment.";
  }

  return "Sorry, I could not complete that just now.\nPlease try again in a moment.";
}

export function ChatWidget() {
  const [storedState] = useState(() => loadStoredChatState());
  const hasStoredConversation = Boolean(storedState?.messages?.length);
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState(
    hasStoredConversation ? storedState.messages : [createWelcomeMessage()]
  );
  const [sessionId, setSessionId] = useState(storedState?.sessionId ?? null);
  const [unreadCount, setUnreadCount] = useState(hasStoredConversation ? storedState.unreadCount : 1);
  const launcherRef = useRef(null);
  const isOpenRef = useRef(isOpen);
  const sessionIdRef = useRef(sessionId);

  useEffect(() => {
    isOpenRef.current = isOpen;
    if (isOpen) {
      setUnreadCount(0);
    }
  }, [isOpen]);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(
      CHAT_STORAGE_KEY,
      JSON.stringify({ messages, sessionId, unreadCount })
    );
  }, [messages, sessionId, unreadCount]);

  function openChat() {
    setIsOpen(true);
  }

  function closeChat() {
    setIsOpen(false);
    launcherRef.current?.focus();
  }

  async function sendMessage(nextMessage) {
    const trimmedMessage = nextMessage.trim();
    if (!trimmedMessage || isSending) {
      return;
    }

    const userMessage = createMessage("user", trimmedMessage);
    const requestSessionId = sessionIdRef.current;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);

    setMessages((currentMessages) => [...currentMessages, userMessage]);
    setInputValue("");
    setIsSending(true);

    try {
      const response = await submitChatMessage(
        {
          message: trimmedMessage,
          session_id: requestSessionId,
        },
        { signal: controller.signal }
      );

      const assistantMessage = createMessage(
        "assistant",
        response?.response?.trim() || "I did not receive a response. Please try again."
      );

      setMessages((currentMessages) => [...currentMessages, assistantMessage]);
      setSessionId(typeof response?.session_id === "string" ? response.session_id : requestSessionId);

      if (!isOpenRef.current) {
        setUnreadCount((currentCount) => currentCount + 1);
      }
    } catch (error) {
      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage("assistant", buildErrorMessage(error), { isError: true }),
      ]);

      if (!isOpenRef.current) {
        setUnreadCount((currentCount) => currentCount + 1);
      }
    } finally {
      window.clearTimeout(timeoutId);
      setIsSending(false);
    }
  }

  function handleSubmit() {
    void sendMessage(inputValue);
  }

  function handleStarterPrompt(prompt) {
    void sendMessage(prompt);
  }

  return (
    <div className="chat-widget">
      <ChatWindow
        inputValue={inputValue}
        isOpen={isOpen}
        isSending={isSending}
        messages={messages}
        onClose={closeChat}
        onInputChange={setInputValue}
        onStarterPrompt={handleStarterPrompt}
        onSubmit={handleSubmit}
        starterPrompts={STARTER_PROMPTS}
      />

      <button
        ref={launcherRef}
        className={`chat-widget__launcher${isOpen ? " is-open" : ""}`}
        type="button"
        aria-expanded={isOpen ? "true" : "false"}
        aria-controls="travel-assistant-panel"
        aria-label={
          isOpen
            ? "Minimize travel assistant"
            : unreadCount > 0
            ? `Open travel assistant. ${unreadCount} unread message${
                unreadCount === 1 ? "" : "s"
              }.`
            : "Open travel assistant"
        }
        onClick={() => (isOpen ? closeChat() : openChat())}
      >
        <span className="chat-widget__launcher-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false">
            <path
              d="M12 3C6.48 3 2 6.94 2 11.8c0 2.67 1.37 5.05 3.54 6.64L5 22l3.58-1.97c1.06.3 2.2.47 3.42.47 5.52 0 10-3.94 10-8.8S17.52 3 12 3Zm-4 9.25a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5Zm4 0a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5Zm4 0a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5Z"
              fill="currentColor"
            />
          </svg>
        </span>
        <span className="chat-widget__launcher-text">Ask LetsGoSA</span>
        {unreadCount > 0 && !isOpen ? (
          <span className="chat-widget__badge" aria-hidden="true">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>
    </div>
  );
}
