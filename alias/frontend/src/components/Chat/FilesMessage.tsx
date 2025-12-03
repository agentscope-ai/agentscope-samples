import React from "react";
import { FilesMessage as FilesMessageType } from "@/types/message";
import { BaseMessage } from "./BaseMessage";
import styles from "./Message.module.scss";
import { FileItems } from "./FileItems";

interface FilesMessageProps {
  message: FilesMessageType;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const FilesMessage: React.FC<FilesMessageProps> = ({
  message,
  onFeedback,
}) => {
  return (
    <BaseMessage message={message} onFeedback={onFeedback}>
      <div className={styles.filesMessage}>
        <div className={styles.filesList}>
          <FileItems files={message.files} />
        </div>
      </div>
    </BaseMessage>
  );
};
