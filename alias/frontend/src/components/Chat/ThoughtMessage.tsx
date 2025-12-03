import React from "react";
import { ThoughtMessage as ThoughtMessageType } from "@/types/message";

interface ThoughtMessageProps {
  message: ThoughtMessageType;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const ThoughtMessage: React.FC<ThoughtMessageProps> = ({ message }) => {
  return (
    <div className="flex items-start gap-2 p-2 bg-gray-50 rounded">
      <span className="text-lg">💭</span>
      <div className="whitespace-pre-wrap">{message.content}</div>
    </div>
  );
};
