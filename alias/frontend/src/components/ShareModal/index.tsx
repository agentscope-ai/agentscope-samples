import { conversationApi } from "@/services/api/conversation";
import { Conversation } from "@/types/api";
import { Button, Input, message, Modal, Switch } from "@agentscope-ai/design";
import copy from "copy-to-clipboard";
import React, { useState } from "react";

import styles from "./index.module.scss";

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  shareUrl: string;
  shared: boolean;
  conversationId: string;
  setCurrentConversation: (con: Conversation) => void;
}

export const ShareModal: React.FC<ShareModalProps> = ({
  isOpen,
  onClose,
  shareUrl,
  shared,
  conversationId,
  setCurrentConversation,
}) => {
  const [copied, setCopied] = useState(false);
  const [isShared, setIsShared] = useState(shared);

  const handleCopy = () => {
    // navigator.clipboard.writeText(shareUrl);
    copy(shareUrl);
    setCopied(true);

    message.success("Share link copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
    onClose();
  };
  const onChangeShare = (share: boolean) => {
    if (!!conversationId) {
      conversationApi
        .shareConversations(conversationId, share)
        .then((res: any) => {
          if (res?.payload) {
            setCurrentConversation(res.payload);
            setIsShared(share);
          }
        })
        .catch((error) => {
          message.error("network error");
        });
    } else setIsShared(share);
  };

  return (
    <Modal
      title="Share This Conversation"
      open={isOpen}
      onCancel={onClose}
      footer={null}
      width={400}
    >
      <div className={styles.container}>
        <div>Are you sure you want to share this conversation?</div>
        <Switch
          className={styles.share}
          checked={isShared}
          onChange={onChangeShare}
          label={isShared ? "Opening" : "Closed"}
        />
        <span></span>
        <div className={styles.urlContainer}>
          <Input
            disabled={!isShared}
            value={shareUrl}
            readOnly
            className={styles.urlInput}
          />
          <Button type="primary" disabled={!isShared} onClick={handleCopy}>
            {copied ? "Copied" : "Copy Link"}
          </Button>
        </div>
        <p className={styles.description}>
          Copy this link and share it with others, they can view the contents of
          this conversation.
        </p>
      </div>
    </Modal>
  );
};
