import { MessageState, Message as MessageType } from "@/types/message";
import { isAtBottom } from "@/utils/sharedRefs";
import React, {
  memo,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Message from "./Message";
import styles from "./MessageList.module.scss";
import { ThinkingMessage } from "./ThinkingMessage";

interface MessageListProps {
  messages?: MessageType[];
  onClarificationSelect?: (options: string[]) => void;
  onAddMessage?: (message: MessageType) => void;
  isThinking?: boolean;
  isReplayMode?: boolean;
  isGenerating?: boolean;
  currentStep?: number;
  ScrollToBottomButtonRef?: any;
  currentConversationId?: string;
  startTimer: () => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages = [],
  onClarificationSelect,
  onAddMessage,
  isThinking = false,
  isReplayMode = false,
  isGenerating = false,
  currentStep,
  currentConversationId,
  ScrollToBottomButtonRef = useRef<any>(),
  startTimer = () => {},
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [displayedMessages, setDisplayedMessages] = useState<MessageType[]>([]);
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [toBottomBtn, setToBottomBtn] = useState(true);
  const messageListRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = () => {
    // console.log(
    //   ScrollToBottomButtonRef.current,
    //   "ScrollToBottomButtonRef.current"
    // );
    if (ScrollToBottomButtonRef.current) {
      // console.log("--------");
      ScrollToBottomButtonRef.current.scrollToBottom("auto");
    }
    // messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Modify message processing logic, add conversation ID filtering
  const processedMessages = useMemo(() => {
    if (!Array.isArray(messages)) {
      return [];
    }

    // First filter out messages belonging to current conversation
    // const currentConversationMessages = messages.filter(msg =>
    //   !currentConversationId || msg.conversation_id === currentConversationId
    // );
    // Sort by time
    const sortedMessages = [...messages].sort(
      (a, b) =>
        new Date(a.create_time).getTime() - new Date(b.create_time).getTime(),
    );

    // Merge consecutive running messages
    return sortedMessages.reduce((acc: MessageType[], curr, index) => {
      // Add directly if it's the first message
      if (index === 0) {
        return [curr];
      }

      const prevMessage = acc[acc.length - 1];
      const isSameConversation =
        curr.conversation_id === prevMessage.conversation_id;
      const isPrevRunning = prevMessage.status === MessageState.RUNNING;
      const isCurrRunning = curr.status === MessageState.RUNNING;
      const isSameType = curr.type === prevMessage.type;

      // If previous message is running state, and current message is also running or finished state
      // and is the same type of message from the same conversation, update the previous message
      if (
        isSameConversation &&
        isPrevRunning &&
        isSameType &&
        (isCurrRunning || curr.status === MessageState.FINISHED)
      ) {
        acc[acc.length - 1] = {
          ...curr,
          id: prevMessage.id, // Keep original id to maintain React key stability
        };
      } else {
        acc.push(curr);
      }

      return acc;
    }, []);
  }, [messages, currentConversationId]);

  // Message streaming output in replay mode
  useEffect(() => {
    // console.log(messages,"processedMessages")

    if (!isReplayMode) {
      setDisplayedMessages(processedMessages);
      return;
    }

    if (currentMessageIndex < processedMessages.length) {
      const currentMessage = processedMessages[currentMessageIndex];
      const messageWithStreaming = {
        ...currentMessage,
        status: MessageState.RUNNING,
      };

      setDisplayedMessages((prev) => [...prev, messageWithStreaming]);

      // Simulate streaming output
      const timer = setTimeout(() => {
        setDisplayedMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...currentMessage,
            status: MessageState.FINISHED,
          };
          return newMessages;
        });
        setCurrentMessageIndex((prev) => prev + 1);
      }, 500); // Display each message for 0.5 seconds

      return () => clearTimeout(timer);
    }
  }, [isReplayMode, currentMessageIndex, processedMessages]);

  // Reset state when message list changes
  useEffect(() => {
    if (isReplayMode) {
      setCurrentMessageIndex(0);
      setDisplayedMessages([]);
    } else {
      setDisplayedMessages(processedMessages);
    }
  }, [messages, isReplayMode, processedMessages]);

  // Update displayed messages when currentStep changes
  useEffect(() => {
    if (currentStep !== undefined) {
      const messagesToShow = processedMessages.slice(0, currentStep);
      setDisplayedMessages(messagesToShow);
      setCurrentMessageIndex(currentStep);
    }
  }, [currentStep, processedMessages]);
  const shouldScrollRef = useRef(isAtBottom.current);

  useEffect(() => {
    // Sync latest scroll condition to ref
    shouldScrollRef.current = isAtBottom.current;
  }, [isAtBottom.current]);
  useLayoutEffect(() => {
    // Exit directly if scrolling is not needed
    if (!shouldScrollRef.current) return;
    startTimer();
  }, [displayedMessages, isThinking, startTimer]);
  useEffect(() => {
    if (toBottomBtn && displayedMessages.length > 0) {
      scrollToBottom();
      setToBottomBtn(false);
    }
  }, [displayedMessages, isThinking]);
  return (
    <div className={styles.messageList} ref={messageListRef}>
      {displayedMessages.map((message) => (
        <Message
          key={message.id}
          message={message}
          messages={displayedMessages}
          onClarificationSelect={onClarificationSelect}
          isReplayMode={isReplayMode}
          isGenerating={isGenerating}
        />
      ))}
      {isThinking && <ThinkingMessage />}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default memo(MessageList);
