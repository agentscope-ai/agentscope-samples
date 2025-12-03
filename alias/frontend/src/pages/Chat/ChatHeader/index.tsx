import React, { memo, useEffect, useState } from "react";
import { Conversation } from "@/types/api";
import { Flex } from "antd";
import {
  SparkStarLine,
  SparkStarFill,
  SparkSettingLine,
  SparkShareLine,
  SparkMessageLine,
} from "@agentscope-ai/icons";
import { conversationApi } from "@/services/api/conversation";
import { ShareModal } from "@/components/ShareModal";

interface ChatHeaderProps {
  currentConversation: Conversation | null;
  languageType: string;
  setLanguageType: (type: string) => void;
  setCurrentConversation: (con: Conversation) => void;
}
const iconStyle = {
  fontSize: "20px",
  cursor: "pointer",
  marginRight: "12px",
};
const ChatHeader: React.FC<ChatHeaderProps> = ({
  currentConversation,
  languageType,
  setCurrentConversation,
}) => {
  const [nowConversation, setNowConversation] = useState<Conversation | null>(
    null,
  );
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);

  useEffect(() => {
    if (currentConversation) setNowConversation(currentConversation);
  }, [currentConversation]);

  const collectedHandle = async () => {
    if (!nowConversation) return;
    const response = await conversationApi.collect(
      nowConversation.id,
      !nowConversation.collected,
    );
    if (response?.payload) {
      setCurrentConversation(response?.payload as Conversation);
    }
  };
  const shareHandle = () => {
    setIsShareModalOpen(true);
  };

  return (
    <>
      <Flex className="h-[56px] pt-4 ml-4 mr-6" justify="space-between">
        <Flex className="p-2 w-4/5">
          <SparkMessageLine style={{ fontSize: 20 }} />
          <div className="ml-2 mr-2">{nowConversation?.name}</div>
          <div onClick={collectedHandle}>
            {!nowConversation?.collected && <SparkStarLine style={iconStyle} />}
            {nowConversation?.collected && (
              <SparkStarFill style={{ ...iconStyle, color: "#ED7E2F" }} />
            )}
          </div>
        </Flex>
        {/* <Flex className="w-1/5 " justify="flex-end">
          <SparkShareLine style={iconStyle} onClick={shareHandle}  />
          <SparkSettingLine style={iconStyle} />
        </Flex> */}
      </Flex>
      {isShareModalOpen && (
        <ShareModal
          isOpen={isShareModalOpen}
          onClose={() => setIsShareModalOpen(false)}
          shared={nowConversation?.shared || false}
          conversationId={nowConversation?.id || ""}
          setCurrentConversation={setCurrentConversation}
          shareUrl={`${window.location.origin}/share/${nowConversation?.user_id}/${nowConversation?.id}?replay=1`}
        />
      )}
    </>
  );
};

export default memo(ChatHeader);
