import React from "react";
import styles from "./Message.module.scss";
import AssistantAvatar from "@/assets/icons/avatar/assistantHeader.png";
import { Flex } from "antd";

export const ThinkingMessage: React.FC = () => {
  return (
    <Flex gap="middle" align="center">
      <div className={styles.avatar}>
        <img src={AssistantAvatar} alt="Agent" />
      </div>
      <div className={styles.thinkingText}>Agent is thinking</div>
      <div className={styles.thinkingDots}>
        <span></span>
        <span></span>
        <span></span>
      </div>
    </Flex>
  );
};
