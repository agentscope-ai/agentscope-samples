import React, { useState, memo } from "react";
import { SparkDoubleRightLine } from "@agentscope-ai/icons";
import styles from "./Message.module.scss";
import type { Message as MessageType } from "@/types/message";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { markdownRegex, codeBlockRegex } from "@/utils/constant";

const CollapsibleMessage: React.FC<{ message: MessageType }> = ({
  message,
}) => {
  const messageContent = message.content;

  const [expandedStates, setExpandedStates] = useState<Record<string, boolean>>(
    {},
  );
  const handleExpand = (messageId: string) => {
    setExpandedStates((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };
  if (messageContent === null || messageContent === undefined) {
    return null;
  }

  if (typeof messageContent !== "string") {
    return JSON.stringify(messageContent, null, 2);
  }

  let content = messageContent;

  if (markdownRegex.test(messageContent)) {
    content = messageContent?.match(markdownRegex)?.[1] || messageContent;
  } else if (codeBlockRegex.test(messageContent)) {
    content = messageContent?.match(codeBlockRegex)?.[1] || messageContent;
  }

  const lines = content.split("\n");
  const showLines = 10;
  const isExpanded = expandedStates[message.id];

  // Determine if we should show full content
  const shouldShowFullContent =
    message.isGenerating || lines.length <= showLines || isExpanded;

  // Calculate visible content
  const visibleContent = shouldShowFullContent
    ? content
    : lines.slice(0, showLines).join("\n");

  return (
    <div className={styles.collapsibleContent}>
      <div className={styles.markdown}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {visibleContent}
        </ReactMarkdown>
      </div>
      {!shouldShowFullContent && (
        <div
          className={`${styles.gradientWrapper} ${
            isExpanded ? styles.expanded : ""
          }`}
        >
          <button
            className={styles.collapseButton}
            onClick={(e) => {
              e.stopPropagation();
              handleExpand(message.id);
            }}
          >
            <SparkDoubleRightLine
              className={`${styles.arrow} ${
                isExpanded ? styles.up : styles.down
              }`}
            />
          </button>
        </div>
      )}
    </div>
  );
};
export default memo(CollapsibleMessage);
