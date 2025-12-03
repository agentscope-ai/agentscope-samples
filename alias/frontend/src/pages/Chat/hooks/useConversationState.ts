import React, { useState, useCallback, useEffect, useRef } from "react";
export const useConversationState = () => {
  const [conversationStates, setConversationStates] = useState<
    Record<
      string,
      {
        isGenerating: boolean;
        taskId: string;
        isThinking: boolean;
      }
    >
  >({});

  const updateConversationState = useCallback(
    (
      conversationId: string,
      state: Partial<{
        isGenerating: boolean;
        taskId: string;
        isThinking: boolean;
      }>,
    ) => {
      if (!conversationId) return;

      setConversationStates((prev) => ({
        ...prev,
        [conversationId]: {
          isGenerating:
            state.isGenerating ?? prev[conversationId]?.isGenerating ?? false,
          taskId: state.taskId ?? prev[conversationId]?.taskId ?? "",
          isThinking:
            state.isThinking ?? prev[conversationId]?.isThinking ?? false,
        },
      }));
    },
    [],
  );

  const getConversationState = useCallback(
    (conversationId: string) => {
      if (!conversationId)
        return { isGenerating: false, taskId: "", isThinking: false };
      return (
        conversationStates[conversationId] || {
          isGenerating: false,
          taskId: "",
          isThinking: false,
        }
      );
    },
    [conversationStates],
  );

  const clearConversationState = useCallback((conversationId: string) => {
    if (!conversationId) return;

    setConversationStates((prev) => {
      const newState = { ...prev };
      delete newState[conversationId];
      return newState;
    });
  }, []);

  return {
    conversationStates,
    updateConversationState,
    getConversationState,
    clearConversationState,
  };
};
