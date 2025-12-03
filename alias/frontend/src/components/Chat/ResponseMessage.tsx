import React from "react";
import { ResponseMessage as ResponseMessageType } from "@/types/message";
import { BaseMessage } from "./BaseMessage";
import styles from "./Message.module.scss";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ResponseMessageProps {
  message: ResponseMessageType;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const ResponseMessage: React.FC<ResponseMessageProps> = ({
  message,
  onFeedback,
}) => {
  return (
    <BaseMessage message={message} onFeedback={onFeedback}>
      <div className={styles.markdown}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
      </div>
    </BaseMessage>
  );
};
