import { useWorkspace } from "@/context/WorkspaceContext.tsx";
import type { ToolCallMessage as ToolCallMessageType } from "@/types/message";
import {
  SparkBrowseLine,
  SparkDownLine,
  SparkLocalFileLine,
  SparkToolLine,
  SparkUpLine,
} from "@agentscope-ai/icons";
import { Flex } from "antd";
import React, { memo, useEffect, useState } from "react";
import styles from "./index.module.scss";

interface ToolCallMessageProps {
  message: ToolCallMessageType;
  onFeedback?: (messageId: string, feedback: "like" | "dislike" | null) => void;
}

export const ToolCallMessage: React.FC<ToolCallMessageProps> = memo(
  ({ message }) => {
    const { setDisplayedContent, setActiveKey, setArgs, setMessageList } =
      useWorkspace();
    const [isExpanded, setIsExpanded] = useState(false);
    useEffect(() => {
      setDisplayedContent(message.content);
      setArgs(message?.arguments);
      setMessageList((prev) => {
        // Filter out old messages with same id
        const filtered = prev.filter(
          (m) => m.id !== message.id && m.content !== message.content,
        );
        // Add new message
        return [...filtered, message];
      });
    }, [message]); // Depend on entire message object

    const getIcon = () => {
      // Determine icon based on tool name if icon is not specified
      if (!message.icon) {
        const toolName =
          ("tool_name" in message ? message.tool_name : undefined) ||
          message.name ||
          "";
        if (toolName.toLowerCase().includes("browser")) {
          return <SparkBrowseLine />;
        }
        if (toolName.toLowerCase().includes("file")) {
          return <SparkLocalFileLine />;
        }
      } else {
        switch (message.icon) {
          case "browser":
            return <SparkBrowseLine />;
          case "file":
            return <SparkLocalFileLine />;
          default:
            return <SparkToolLine />;
        }
      }
      return <SparkToolLine />;
    };

    const getToolName = () => {
      if (message.type === "tool_use")
        return `Using Tool: ${message?.tool_name || message.name}`;
      if (message.type === "tool_result")
        return `Tool result: ${message?.tool_name || message.name}`;
      return message?.tool_name || message.name;
    };

    const getToolArguments = () => {
      const argContents = JSON.stringify(message.arguments, null, 2);
      if (!argContents || argContents === "{}" || argContents === "{ }") {
        try {
          const content = JSON.parse(message.content);
          if (Array.isArray(content) && content.length > 0) {
            const output = content[0]?.output;
            if (typeof output === "string") {
              return output;
            }
            if (Array.isArray(output) && output.length > 0) {
              return JSON.stringify(output?.[0], null, 2);
            }
          }
        } catch (error) {
          // Return original content or empty string if parsing fails
          console.error("Failed to parse message content:", error);
          return message.content || "";
        }
      }
      return argContents;
    };
    return (
      <Flex vertical className={styles.toolCallMessage}>
        <Flex
          gap="small"
          justify="space-between"
          className={styles.toolCallHeader}
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
            setDisplayedContent(message.content);
            setArgs(message.arguments);
            setActiveKey("1");
          }}
        >
          <Flex gap="small">
            {getIcon()}
            {getToolName()}
          </Flex>
          {!isExpanded ? <SparkDownLine /> : <SparkUpLine />}
        </Flex>
        {isExpanded && message.arguments && (
          <div className={styles.arguments}>
            <div className={styles.contents}>{getToolArguments()}</div>
          </div>
        )}
      </Flex>
    );
  },
);
