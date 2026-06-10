function formatTimestamp(value) {
  if (!value) {
    return "";
  }

  try {
    return new Intl.DateTimeFormat([], {
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return "";
  }
}

export function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const authorLabel = isUser ? "You" : "LetsGoSA travel assistant";
  const timestamp = formatTimestamp(message.createdAt);

  return (
    <article
      className={`chat-message chat-message--${message.role}${
        message.isError ? " chat-message--error" : ""
      }`}
    >
      <div className="chat-message__meta">
        <span>{authorLabel}</span>
        {timestamp ? <time dateTime={message.createdAt}>{timestamp}</time> : null}
      </div>

      <div
        className={`chat-message__bubble${
          message.isTyping ? " chat-message__bubble--typing" : ""
        }`}
      >
        {message.isTyping ? (
          <span className="chat-typing" aria-label="Assistant is typing">
            <span />
            <span />
            <span />
          </span>
        ) : (
          message.content
        )}
      </div>
    </article>
  );
}
