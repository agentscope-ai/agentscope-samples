import AssistantAvatar from "@/assets/icons/avatar/assistantHeader.png";
import correctCheckIcon from "@/assets/icons/check/correct-checkCircle-line.svg";
import pendingCheckIcon from "@/assets/icons/check/pending-checkCircle-line.svg";
import type {
  ClarificationMessage,
  FilesMessage,
  Message as MessageType,
  ToolCallMessage,
} from "@/types/message";
import {
  MessageRole,
  MessageState,
  MessageType as MsgType,
} from "@/types/message";
import { Flex } from "antd";
import React, { memo, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { ClarificationMessage as ClarificationMessageComponent } from "./ClarificationMessage";
import CollapsibleMessage from "./CollapsibleMessage";
import { FilesMessage as FilesMessageComponent } from "./FilesMessage";
import styles from "./Message.module.scss";
import { ToolCallMessage as ToolCallMessageComponent } from "./ToolCallMessage";
import { UserMessage } from "./UserMessage";

interface MessageProps {
  message: MessageType;
  onClarificationSelect?: (options: string[]) => void;
  isReplayMode?: boolean;
  isGenerating?: boolean;
  messages?: MessageType[];
}

const deduplicateMessages = (messages: MessageType[]): MessageType[] => {
  const result: MessageType[] = [];
  let consecutiveSubResponses: MessageType[] = [];

  // Handle consecutive SUB_RESPONSE
  const processConsecutiveSubResponses = () => {
    if (consecutiveSubResponses.length > 0) {
      // Deduplicate consecutive SUB_RESPONSE
      const uniqueMessages = new Map<string, MessageType>();
      consecutiveSubResponses.forEach((msg) => {
        const key = `${msg.name}-${msg.content}`;
        if (uniqueMessages.has(key)) {
          const existingMsg = uniqueMessages.get(key)!;
          if (
            new Date(msg.create_time).getTime() >
            new Date(existingMsg.create_time).getTime()
          ) {
            uniqueMessages.set(key, msg);
          }
        } else {
          uniqueMessages.set(key, msg);
        }
      });

      // Add deduplicated messages to result
      result.push(...Array.from(uniqueMessages.values()));
      consecutiveSubResponses = []; // Clear temporary array
    }
  };

  messages.forEach((msg, index) => {
    if (msg.type === MsgType.SUB_RESPONSE) {
      consecutiveSubResponses.push(msg);
    } else {
      // When encountering non-SUB_RESPONSE message, process previously collected consecutive SUB_RESPONSE
      processConsecutiveSubResponses();
      // Add non-SUB_RESPONSE message
      result.push(msg);
    }
  });

  // Process last group of consecutive SUB_RESPONSE
  processConsecutiveSubResponses();

  return result;
};
export const Message: React.FC<MessageProps> = ({
  message,
  onClarificationSelect,
  isReplayMode = false,
  isGenerating = false,
  messages = [],
}) => {
  const isUser = message.role === MessageRole.USER;
  const [openPopoverId, setOpenPopoverId] = useState<string | null>(null);
  const location = useLocation();
  const isSharePage = location.pathname.includes("/share/");

  const renderAvatar = () => {
    return (
      <Flex gap="middle">
        <div className={styles.avatar}>
          <img src={AssistantAvatar} alt="Assistant" />
        </div>
        <div className={styles.assistantTitle}>Alias Agent</div>
      </Flex>
    );
  };

  // Render directly if it's a user message
  if (isUser && message.type === MsgType.USER)
    return <UserMessage message={message} />;
  // For agent messages, only render the entire group for the first message
  const isFirstMessage =
    messages.find(
      (msg) =>
        msg.role === MessageRole.ASSISTANT &&
        msg.parent_message_id === message.parent_message_id,
    )?.id === message.id;

  if (!isFirstMessage) {
    return null;
  }

  // Modify renderStatus function
  const renderStatus = () => {
    if (!message.isGenerating) {
      return null;
    }
    if (
      message.status !== MessageState.WAITING &&
      message.status !== MessageState.ERROR
    ) {
      return (
        <div className={`${styles.status} ${styles.running}`}>
          Generating...
        </div>
      );
    }
    return (
      <div
        className={`${styles.status} ${styles[message.status.toLowerCase()]}`}
      >
        {message.status === MessageState.WAITING && "Waiting..."}
        {message.status === MessageState.ERROR && "Generation failed"}
      </div>
    );
  };

  const renderSingleMessage = (
    msg: MessageType,
    allMessages: MessageType[],
  ) => {
    switch (msg.type) {
      case MsgType.RESPONSE:
        return (
          <div key={msg.id} className={styles.response}>
            <div className={styles.content}>
              <CollapsibleMessage message={msg} />
            </div>
          </div>
        );

      case MsgType.THOUGHT:
        return (
          <div key={msg.id} className={styles.thought}>
            <CollapsibleMessage message={msg} />
          </div>
        );

      case MsgType.SUB_RESPONSE:
        return (
          <div key={msg.id}>
            <div className={styles.subResponse}>
              <img
                src={
                  msg.status === MessageState.FINISHED
                    ? correctCheckIcon
                    : pendingCheckIcon
                }
                alt="status"
                className={styles.icon}
              />
              <div className={styles.content}>
                <CollapsibleMessage message={msg} />
              </div>
            </div>
          </div>
        );

      case MsgType.SUB_THOUGHT:
        return (
          <div className={styles.subMessageItem}>
            <div key={msg.id} className={styles.thought}>
              <CollapsibleMessage message={msg} />
            </div>
          </div>
        );
      case MsgType.TOOL_CALL:
      case MsgType.TOOL_USE:
      case MsgType.TOOL_RESULT:
        return (
          <div
            key={msg.id}
            className={styles.toolCallWrapper}
            id={`message-toolcall-${msg.id}`}
          >
            <ToolCallMessageComponent message={msg as ToolCallMessage} />
          </div>
        );

      case MsgType.CLARIFICATION:
        if (!msg.content && (msg?.options?.length === 0 || !msg?.options))
          return null;
        return (
          <div key={msg.id} className={styles.clarificationMessage}>
            <ClarificationMessageComponent
              message={msg as ClarificationMessage}
              onSelect={onClarificationSelect}
            />
          </div>
        );

      case MsgType.FILES:
        return (
          <div key={msg.id} className={styles.fileSection}>
            <FilesMessageComponent message={msg as FilesMessage} />
          </div>
        );

      default:
        return null;
    }
  };

  // Get all non-user messages with the same parent_message_id
  const relatedMessages = useMemo(() => {
    const filteredMessages = messages.filter(
      (msg) =>
        msg.role === MessageRole.ASSISTANT &&
        msg.parent_message_id === message.parent_message_id,
    );

    // Deduplicate messages
    const uniqueMessages = deduplicateMessages(filteredMessages);
    return uniqueMessages;
  }, [messages, message.parent_message_id]);

  if (relatedMessages && relatedMessages.length === 0) {
    return null;
  }

  return (
    <div className={styles.messageWrapper}>
      {renderAvatar()}
      <div className={styles.messageContent}>
        {relatedMessages.map((msg, index) => {
          return (
            <div
              className={`${styles.messageItem} ${
                openPopoverId === msg.id ? styles.selectedMessage : ""
              }`}
              key={msg.id}
            >
              {renderSingleMessage(msg, relatedMessages)}
            </div>
          );
        })}
        <div className={styles.messageFooter}>{renderStatus()}</div>
      </div>
    </div>
  );
};
export default memo(Message);
