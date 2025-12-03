import { Conversation } from "@/types/api";
import React, { createContext, ReactNode, useContext, useState } from "react";

interface MessageContextType {
  currentConversation: Conversation | null; // Modified to allow null type
  setCurrentConversation: (conversation: Conversation | null) => void;
}

const MessageContext = createContext<MessageContextType | undefined>(undefined);

export const MessageProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [currentConversation, setCurrentConversation] =
    useState<Conversation | null>(null);
  return (
    <MessageContext.Provider
      value={{
        currentConversation,
        setCurrentConversation,
      }}
    >
      {children}
    </MessageContext.Provider>
  );
};

export const useMessage = () => {
  const context = useContext(MessageContext);
  if (context === undefined) {
    throw new Error("useMessage must be used within a MessageProvider");
  }
  return context;
};
