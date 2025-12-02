import React, { memo, useRef, useLayoutEffect } from "react";
import { Button } from "@agentscope-ai/design";
import { Flex } from "antd";
import { SparkEditLine } from "@agentscope-ai/icons";
import { useWorkspace } from "@/context/WorkspaceContext";
import { isAtBottom } from "@/utils/sharedRefs";

interface RoadmapButtonProps {
  handleSendMessage: (message: string) => void;
  setShow: (show: boolean) => void;
  startTimer: () => void;
  setShowRoadmapEditBtn: (edit: boolean) => void;
}
const RoadmapButton: React.FC<RoadmapButtonProps> = ({
  handleSendMessage,
  setShow,
  startTimer,
  setShowRoadmapEditBtn,
}) => {
  const { setActiveKey } = useWorkspace();
  const shouldScrollRef = useRef(isAtBottom.current);
  useLayoutEffect(() => {
    if (!shouldScrollRef.current) return;
    startTimer();
  }, [startTimer]);
  const acceptedRoadmap = () => {
    const acceptedMessage =
      "I have accepted the Roadmap, please proceed with the execution";
    handleSendMessage(acceptedMessage);
    setShow(false);
  };
  return (
    <Flex gap={16} align="center" style={{ paddingBottom: 80 }}>
      <Button
        onClick={() => {
          setActiveKey("roadmap");
          setShow(false);
          setShowRoadmapEditBtn(true);
        }}
      >
        <SparkEditLine /> Edit Roadmap
      </Button>
      <Button onClick={acceptedRoadmap}>
        <SparkEditLine /> Accept Roadmap
      </Button>
    </Flex>
  );
};

export default memo(RoadmapButton);
