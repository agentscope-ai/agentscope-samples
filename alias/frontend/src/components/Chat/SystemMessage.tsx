import React from "react";
import { SystemMessage as SystemMessageType } from "@/types/message";
import { BaseMessage } from "./BaseMessage";

interface SystemMessageProps {
  message: SystemMessageType;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const SystemMessage: React.FC<SystemMessageProps> = ({
  message,
  onFeedback,
}) => {
  return (
    <BaseMessage message={message} onFeedback={onFeedback}>
      <div>{message.content}</div>
    </BaseMessage>
  );
};
