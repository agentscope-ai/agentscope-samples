import React from "react";
import { SubResponseMessage as SubResponseMessageType } from "@/types/message";
import { BaseMessage } from "./BaseMessage";
import styles from "./Message.module.scss";

interface SubResponseMessageProps {
  message: SubResponseMessageType;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const SubResponseMessage: React.FC<SubResponseMessageProps> = ({
  message,
  onFeedback,
}) => {
  return (
    <BaseMessage message={message} onFeedback={onFeedback}>
      <div className={styles.subResponseMessage}>
        {/* <img src={iconCheckbox} alt="checkbox" className={styles.checkbox} /> */}
        <div className={styles.subResponseContent}>{message.content}</div>
      </div>
    </BaseMessage>
  );
};
