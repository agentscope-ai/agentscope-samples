import React from "react";
import { SubThoughtMessage as SubThoughtMessageType } from "@/types/message";
import { BaseMessage } from "./BaseMessage";
import styles from "./Message.module.scss";

interface SubThoughtMessageProps {
  message: SubThoughtMessageType;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const SubThoughtMessage: React.FC<SubThoughtMessageProps> = ({
  message,
  onFeedback,
}) => {
  return (
    <BaseMessage message={message} onFeedback={onFeedback}>
      <div className={styles.subThoughtMessage}>
        <div className={styles.subThoughtContent}>{message.content}</div>
      </div>
    </BaseMessage>
  );
};
