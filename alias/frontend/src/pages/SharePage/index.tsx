import iconProgressDot from "@/assets/icons/sharePage/circle401.svg";
import iconPause from "@/assets/icons/sharePage/pause.svg";
import iconPlay from "@/assets/icons/sharePage/play.svg";
import iconStepBack from "@/assets/icons/sharePage/step-back.svg";
import iconStepForward from "@/assets/icons/sharePage/step-forward.svg";
import { MessageList } from "@/components/Chat/MessageList";
import Roadmap from "@/components/Roadmap";
import Workspace from "@/components/Workspace";
import { useWorkspace } from "@/context/WorkspaceContext";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import styles from "./index.module.scss";

import ScrollToBottomButton from "@/components/ScrollToBottomButton";
import { conversationApi } from "@/services/api/conversation";
import { ApiMessage } from "@/types/api";
import {
  FeedbackType,
  Message,
  MessageRole,
  MessageState,
  MessageType,
  SelectionType,
  ToolIconType,
} from "@/types/message";
import { RoadMap } from "@/types/roadmap";

const SharePage: React.FC = () => {
  const { sessionId, userId } = useParams<{
    userId: string;
    sessionId: string;
  }>();
  const [searchParams] = useSearchParams();
  const isReplayMode = searchParams.get("replay") === "1";
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [isPlaying, setIsPlaying] = useState(isReplayMode);
  const [roadmapData, setRoadmapData] = useState<RoadMap | null>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const { setDisplayedContent } = useWorkspace();
  const totalSteps = messages.length;
  const [activeTab, setActiveTab] = useState<"workspace" | "roadmap">(
    "workspace",
  );
  const timerIdRef = useRef<NodeJS.Timeout | null>(null);
  const ScrollToBottomButtonRef = useRef<any>(null);
  const [conversationName, setConversationName] = useState<string>("");
  const startTimer = () => {
    if (ScrollToBottomButtonRef?.current) {
      ScrollToBottomButtonRef.current.scrollToBottom("auto");
    }
  };

  const calculateProgressDotPosition = useCallback(
    (step: number) => {
      if (totalSteps <= 1) return "0%";
      const progress = ((step - 1) / (totalSteps - 1)) * 100;
      return `${Math.min(Math.max(progress, 0), 100)}%`;
    },
    [totalSteps],
  );

  const onNextStep = useCallback(() => {
    if (currentStep < totalSteps) {
      setCurrentStep((prev) => prev + 1);
    }
  }, [currentStep, totalSteps]);

  const onPrevStep = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  const handleProgressClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!progressRef.current) return;
      const rect = progressRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = x / rect.width;
      const newStep = Math.max(
        1,
        Math.min(totalSteps, Math.round(percentage * totalSteps)),
      );
      setCurrentStep(newStep);
    },
    [totalSteps],
  );

  const handleProgressDrag = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.buttons !== 1) return; // Only handle when left mouse button is pressed
      handleProgressClick(e);
    },
    [handleProgressClick],
  );

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isPlaying && currentStep < totalSteps) {
      timer = setTimeout(() => {
        setCurrentStep((prev) => prev + 1);
      }, 1000); // Play one message per second
    } else if (currentStep === totalSteps) {
      setIsPlaying(false);
    }
    return () => clearTimeout(timer);
  }, [isPlaying, currentStep, totalSteps]);

  const mapApiMessageToChatMessage = (msg: ApiMessage): Message => {
    const baseMessage = {
      ...msg?.message,
      id: msg.id,
      role:
        msg.message.role === "user" ? MessageRole.USER : MessageRole.ASSISTANT,
      content: msg.message.content,
      status: msg.message.status as MessageState,
      create_time: msg.create_time,
      update_time: msg.update_time,
      feedback: msg.feedback
        ? msg.feedback === "like"
          ? FeedbackType.LIKE
          : FeedbackType.DISLIKE
        : null,
      conversation_id: msg.conversation_id,
      parent_message_id: msg.parent_message_id || "",
    };

    // Return directly if it's a user message
    if (msg.message.role === "user") {
      return {
        ...baseMessage,
        type: MessageType.USER,
      };
    }

    // Determine agent message type
    switch (msg.message.type) {
      case "response":
        return {
          ...baseMessage,
          type: MessageType.RESPONSE,
        };
      case "thought":
        return {
          ...baseMessage,
          type: MessageType.THOUGHT,
        };
      case "sub_response":
        return {
          ...baseMessage,
          type: MessageType.SUB_RESPONSE,
        };
      case "sub_thought":
        return {
          ...baseMessage,
          type: MessageType.SUB_THOUGHT,
        };
      case "tool_call":
        return {
          ...baseMessage,
          type: MessageType.TOOL_CALL,
          name: msg.message.name || "",
          arguments: msg.message.arguments || {},
          icon: (msg.message.icon as ToolIconType) || ToolIconType.TOOL,
          content: msg.message.content,
          tool_name: msg.message.tool_name || "",
        };

      case "tool_use":
        return {
          ...baseMessage,
          type: MessageType.TOOL_USE,
          name: msg.message.name || "",
          arguments: msg.message.arguments || {},
          icon: (msg.message.icon as ToolIconType) || ToolIconType.TOOL,
          content: msg.message.content,
          tool_name: msg.message.tool_name || "",
        };
      case "tool_result":
        return {
          ...baseMessage,
          type: MessageType.TOOL_RESULT,
          name: msg.message.name || "",
          arguments: msg.message.arguments || {},
          icon: (msg.message.icon as ToolIconType) || ToolIconType.TOOL,
          content: msg.message.content,
          tool_name: msg.message.tool_name || "",
        };
      case "clarification":
        return {
          ...baseMessage,
          type: MessageType.CLARIFICATION,
          options: msg.message.options || [],
          selection_type:
            msg.message.selection_type === "multiple"
              ? SelectionType.MULTIPLE
              : SelectionType.SINGLE,
        };
      case "files":
        return {
          ...baseMessage,
          type: MessageType.FILES,
          files: msg.message.files || [],
        };
      default:
        return {
          ...baseMessage,
          type: MessageType.RESPONSE,
        };
    }
  };

  useEffect(() => {
    const loadData = async () => {
      if (!sessionId || !userId) {
        setError("Session ID does not exist");
        setLoading(false);
        return;
      }

      try {
        // const [messagesResponse, roadmapResponse] = await Promise.all([
        //   conversationApi.getMessages(sessionId),
        //   conversationApi.getRoadmap(sessionId),
        // ]);

        // if (messagesResponse.status && messagesResponse.payload) {
        //   const apiResponse = messagesResponse as unknown as ApiResponse<
        //     ListResponsePayload<ApiMessage>
        //   >;
        //   const apiMessages = apiResponse.payload.items;
        //   if (apiMessages && apiMessages.length > 0) {
        //     const mappedMessages = apiMessages.map(
        //       mapApiMessageToChatMessage,
        //     ) as Message[];
        //     setMessages(mappedMessages);
        //   }
        // }

        // if (roadmapResponse.status && roadmapResponse.payload) {
        //   setRoadmapData(roadmapResponse.payload as unknown as RoadMap);
        // }
        const res = await conversationApi.getShareConversations(
          userId,
          sessionId,
        );
        if (res.status === true && res.payload) {
          const apiMessages = res.payload?.messages || [];
          const roadmapResponse = res.payload?.roadmap || {};
          if (
            apiMessages &&
            Array.isArray(apiMessages) &&
            apiMessages.length > 0
          ) {
            const mappedMessages = apiMessages.map(
              mapApiMessageToChatMessage,
            ) as Message[];
            setMessages(mappedMessages);
          }
          if (roadmapResponse) setRoadmapData(roadmapResponse as RoadMap);
          setConversationName(res.payload.name);
        }
      } catch (err) {
        setError("Failed to load data");
        console.error("Failed to load data:", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [sessionId]);

  // Display messages based on current step
  const displayedMessages = messages.slice(0, currentStep);

  if (loading) {
    return <div className={styles.loading}>Loading...</div>;
  }

  if (error) {
    return <div className={styles.error}>Error: {error}</div>;
  }

  return (
    <div className={styles.sharePage}>
      <div className={styles.mainContent}>
        <div className={styles.messageList} style={{ flex: 1 }}>
          <div className={styles.conversationName}>
            Conversation Name: {conversationName}
          </div>
          <ScrollToBottomButton
            className={styles.scrollWrapper}
            autoScrollThreshold={5}
            ref={ScrollToBottomButtonRef}
          >
            <MessageList
              startTimer={startTimer}
              messages={displayedMessages}
              isReplayMode={isReplayMode}
              currentStep={currentStep}
              ScrollToBottomButtonRef={ScrollToBottomButtonRef}
            />
          </ScrollToBottomButton>
        </div>
        <div
          className={styles.rightTabs}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
          }}
        >
          <div className={styles.tabHeader}>
            <div
              className={
                activeTab === "workspace" ? styles.tabActive : styles.tab
              }
              onClick={() => setActiveTab("workspace")}
            >
              AGENT WORKSPACE
            </div>
            <div
              className={
                activeTab === "roadmap" ? styles.tabActive : styles.tab
              }
              onClick={() => setActiveTab("roadmap")}
            >
              ROADMAP
            </div>
          </div>
          <div className={styles.tabContent}>
            {activeTab === "workspace" ? (
              <Workspace
                conversationId={sessionId || ""}
                currentStep={currentStep}
                totalSteps={totalSteps}
                onNextStep={onNextStep}
                onPrevStep={onPrevStep}
                todoList={null}
                hideHeader={true}
              />
            ) : (
              <Roadmap
                data={roadmapData || undefined}
                editable={false}
                conversationId={sessionId || ""}
              />
            )}
          </div>
        </div>
      </div>
      {messages.length > 0 && (
        <div className={styles.progressBar}>
          <div className={styles.progressContainer}>
            <button
              className={styles.controlButton}
              onClick={onPrevStep}
              disabled={currentStep === 1}
              title="Step Back"
            >
              <img src={iconStepBack} alt="Step Back" />
            </button>
            <button
              className={styles.controlButton}
              onClick={() => setIsPlaying(!isPlaying)}
              title={isPlaying ? "Pause" : "Play"}
            >
              <img
                src={isPlaying ? iconPause : iconPlay}
                alt={isPlaying ? "Pause" : "Play"}
              />
            </button>
            <button
              className={styles.controlButton}
              onClick={onNextStep}
              disabled={currentStep === totalSteps}
              title="Step Forward"
            >
              <img src={iconStepForward} alt="Step Forward" />
            </button>
            <div
              className={styles.progress}
              ref={progressRef}
              onClick={handleProgressClick}
              onMouseMove={handleProgressDrag}
            >
              <div
                className={styles.progressDot}
                style={{ left: calculateProgressDotPosition(currentStep) }}
              >
                <img src={iconProgressDot} alt="" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SharePage;
