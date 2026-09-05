// Manage the expanding chat input, focus, and Enter-to-send keyboard behavior.

import { useEffect, useId, useRef } from "react";

export function ChatInput({ disabled, onChange, onSubmit, shouldFocus, value }) {
  const inputId = useId();
  const textareaRef = useRef(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, [value]);

  useEffect(() => {
    if (!shouldFocus) {
      return;
    }

    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  }, [shouldFocus]);

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit();
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor={inputId}>
        Message the LetsGoSA travel assistant
      </label>
      <textarea
        id={inputId}
        ref={textareaRef}
        className="chat-input__field"
        rows={1}
        enterKeyHint="send"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about packages, destinations, pricing, or bookings..."
        aria-label="Type your message"
        disabled={disabled}
      />
      <button
        className="button chat-input__submit"
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label={disabled ? "Sending message" : "Send message"}
      >
        {disabled ? "Sending..." : "Send"}
      </button>
    </form>
  );
}
