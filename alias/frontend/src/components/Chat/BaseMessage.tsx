import { Message, MessageRole, MessageState } from "@/types/message";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import styles from "./Message.module.scss";

interface BaseMessageProps {
  message: Message;
  children: React.ReactNode;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const BaseMessage: React.FC<BaseMessageProps> = ({
  message,
  children,
  onFeedback,
}) => {
  const isAssistant = message.role === MessageRole.ASSISTANT;
  const isRunning = message.status === MessageState.RUNNING;
  const isWaiting = message.status === MessageState.WAITING;
  const isError = message.status === MessageState.ERROR;

  const renderContent = (content: React.ReactNode) => {
    if (typeof content === "string") {
      return (
        <div className={styles.markdown}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      );
    }
    return content;
  };

  return (
    <div
      className={`${styles.message} ${
        isAssistant ? styles.assistant : styles.user
      }`}
    >
      <div className={styles.content}>
        {renderContent(children)}
        {isRunning && <div className={styles.loading}>...</div>}
        {isWaiting && (
          <div className={styles.waiting}>Waiting for user selection...</div>
        )}
        {isError && <div className={styles.error}>An error occurred</div>}
      </div>
      {isAssistant && onFeedback && (
        <div className={styles.feedback}>
          <button
            className={`${styles.feedbackBtn} ${
              message.feedback === "like" ? styles.active : ""
            }`}
            onClick={() =>
              onFeedback(
                message.id,
                message.feedback === "like" ? null : "like",
              )
            }
          >
            👍
          </button>
          <button
            className={`${styles.feedbackBtn} ${
              message.feedback === "dislike" ? styles.active : ""
            }`}
            onClick={() =>
              onFeedback(
                message.id,
                message.feedback === "dislike" ? null : "dislike",
              )
            }
          >
            👎
          </button>
        </div>
      )}
    </div>
  );
};
