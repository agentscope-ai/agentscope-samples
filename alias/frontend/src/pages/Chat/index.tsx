import { MessageList } from "@/components/Chat/MessageList";
import LoginModal from "@/components/LoginModal";
import Roadmap from "@/components/Roadmap";
import SandBox from "@/components/SandBox";
import ScrollToBottomButton from "@/components/ScrollToBottomButton";
import Workspace from "@/components/Workspace";
import { useMessage } from "@/context/MessageContext";
import { useWorkspace } from "@/context/WorkspaceContext.tsx";
import { conversationApi } from "@/services/api/conversation";
import {
  ApiMessage,
  ApiResponse,
  Conversation,
  FilePreview as FilePreviewProps,
  ListResponsePayload,
  SSEResponse,
} from "@/types/api";
import {
  Message,
  MessageRole,
  MessageState,
  MessageType,
} from "@/types/message";
import { RoadMapDataProps, RoadMapMessage, RoadMapType } from "@/types/roadmap";
import { ChatModeType, LANGUAGETYPE } from "@/utils/constant";
import { isAtBottom } from "@/utils/sharedRefs";
import { message, Tabs, type TabsProps } from "@agentscope-ai/design";
import useUrlState from "@ahooksjs/use-url-state";
import dayjs from "dayjs";
import { useCallback, useEffect, useRef, useState } from "react";
import ChatHeader from "./ChatHeader";
import ChatInput from "./ChatInput";
import ChatMode from "./ChatMode";
import styles from "./index.module.scss";
import Prompts from "./Prompts";
import RoadmapButton from "./RoadmapButton";
import Sidebar from "./Sidebar";
import { mapApiMessageToChatMessage, getPromptFile } from "./utils";
import WelcomeView from "./WelcomeView";

export const Chat = () => {
  const [state, setState] = useUrlState({ conversationId: "" });
  const { conversationId } = state;
  const { setCurrentConversation, currentConversation } = useMessage();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const { activeKey, setActiveKey } = useWorkspace();
  const [isGenerating, setIsGenerating] = useState(false);
  const [filePreview, setFilePreview] = useState<FilePreviewProps[]>([]);
  const [roadmapData, setRoadmapData] = useState<RoadMapDataProps | null>(null);
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingConversationId, setThinkingConversationId] = useState<
    string | null
  >(null);
  const [chatMode, setChatMode] = useState<ChatModeType>(ChatModeType.GENERAL);
  const roadmapUpdateQuery = "I have updated the task content";
  const ScrollToBottomButtonRef = useRef<any>(null);
  const [taskId, setTaskId] = useState(""); // task_id is needed to stop conversation
  const [languageType, setLanguageType] = useState<string>(LANGUAGETYPE.en_US);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [showRoadmapSelectBtn, setShowRoadmapSelectBtn] = useState(false); // Show roadmap button
  const [showRoadmapEditBtn, setShowRoadmapEditBtn] = useState(false);
  // Cancel ongoing requests when component unmounts
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);
  useEffect(() => {
    // setOnDoneCallback(async (conversationId, taskId, messageId) => {
    // });
    if (
      roadmapData &&
      roadmapData?.subtasks &&
      Array.isArray(roadmapData?.subtasks)
    ) {
      const subtasks = roadmapData?.subtasks.filter(
        (item) => item.state === RoadMapType.TODO,
      );
      if (
        subtasks.length > 0 &&
        subtasks.length === roadmapData?.subtasks?.length &&
        !isGenerating &&
        !isThinking
      ) {
        setShowRoadmapSelectBtn(true);
      } else {
        setShowRoadmapSelectBtn(false);
      }
    }
  }, [roadmapData]);

  // Handle roadmap data updates
  useEffect(() => {
    const handleRoadmapUpdate = (message: any) => {
      if (
        message.type === MessageType.RESPONSE &&
        typeof message.content === "object" &&
        message.content !== null &&
        "data" in message.content &&
        message.content.data?.roadmap &&
        Object.keys(message.content?.data?.roadmap).length > 0
      ) {
        setRoadmapData(message.content.data.roadmap as RoadMapDataProps);
      }
    };

    if (messages) {
      messages.forEach(handleRoadmapUpdate);
    }
  }, [messages]);
  useEffect(() => {
    const loadConversationFromStorage = async () => {
      if (conversationId) {
        await handleGetMessages(conversationId);
        await handleGetRoadmap(conversationId);
        await handleGetCurConversation(conversationId);
      }
    };
    loadConversationFromStorage();
  }, []);
  const createNewConversation = async (
    name: string,
    description: string,
    chatMode: string,
  ) => {
    try {
      const defaultName = `Conversation ${dayjs().format("YYYY-MM-DD HH:mm")}`;
      const response = await conversationApi.create(
        name || defaultName,
        description || "empty",
        chatMode,
      );
      if (!response.status || !response.payload) {
        throw new Error("Failed to create conversation");
      }
      const targetConversationId = response.payload.id;
      const newConversation: Conversation = {
        id: targetConversationId,
        name: name || defaultName,
        description: description || "empty",
        runtime_status: "running",
        create_time: new Date().toISOString(),
        update_time: new Date().toISOString(),
        user_id: response.payload.user_id,
        artifacts_sio: response?.payload?.artifacts_sio || "",
        browser_ws: response?.payload?.browser_ws || "",
        runtime_token: response?.payload?.runtime_token || "",
        shared: response?.payload?.shared || false,
        sandbox_url: response?.payload?.sandbox_url || "",
        chat_mode: response?.payload?.chat_mode || ChatModeType.GENERAL,
      };
      setCurrentConversation(newConversation);
      setChatMode(response?.payload?.chat_mode || ChatModeType.GENERAL);
      return targetConversationId;
    } catch (error) {
      console.error("Failed to create conversation:", error);
      throw error;
    }
  };
  const startTimer = useCallback(() => {
    if (ScrollToBottomButtonRef?.current) {
      ScrollToBottomButtonRef.current.scrollToBottom("auto");
    }
  }, []);
  const resetThinkingState = () => {
    setIsThinking(false);
    setThinkingConversationId(null);
  };
  const sendMessageWithHandling = async (
    conversationId: string,
    content: string,
    parentMessageId: string,
    fileIds?: string[],
    roadmap?: RoadMapMessage | null,
  ) => {
    setIsThinking(true);
    setThinkingConversationId(conversationId);
    // Create new AbortController
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    try {
      await conversationApi.sendMessage(
        conversationId,
        content,
        (parsed: SSEResponse) => {
          if (parsed.data.messages && parsed.data.messages.length > 0) {
            setMessages((prevMessages) => {
              const newMessages = parsed.data.messages.map((msg) => {
                const chatMessage = mapApiMessageToChatMessage(msg, true);
                return {
                  ...chatMessage,
                  timestamp: Date.now(),
                };
              });
              const updatedMessages = prevMessages.slice();
              newMessages.forEach((newMsg) => {
                const index = updatedMessages.findIndex(
                  (existingMsg) => existingMsg.id === newMsg.id,
                );
                if (index !== -1) {
                  updatedMessages[index] = newMsg;
                } else {
                  updatedMessages.push(newMsg);
                }
              });
              return updatedMessages;
            });
            resetThinkingState();
            if (parsed?.task_id) setTaskId(parsed.task_id);
          }
          // Can stop message if messages is empty array and has task_id
          if (
            parsed.data.messages &&
            parsed.data.messages.length === 0 &&
            parsed?.task_id
          ) {
            setTaskId(parsed.task_id);
          }
          if (
            parsed.data.roadmap &&
            Object.keys(parsed.data.roadmap).length > 0
          ) {
            setRoadmapData(parsed.data.roadmap);
          }
        },
        (error: any) => {
          // Don't show error message if it's a cancel operation
          if (error.name === "AbortError" || abortController.signal.aborted) {
            resetThinkingState();
            return;
          }
          message.error({
            content: error.message || "Request failed, please try again later",
            duration: 3,
          });
          setTimeout(() => {
            resetThinkingState();
          }, 1000);
          throw error;
        },
        "task",
        fileIds ? fileIds : [],
        languageType,
        chatMode,
        abortController,
        roadmap,
      );
    } catch (error: any) {
      // Don't show error message if it's a cancel operation
      if (error.name === "AbortError" || abortController.signal.aborted) {
        resetThinkingState();
        return;
      }
      console.error("API call failed:", error);
      // Remove thinking state on error
      resetThinkingState();

      const errorMessage: Message = {
        id: Date.now().toString(),
        role: MessageRole.ASSISTANT,
        content: "Error, please try again later.",
        status: MessageState.ERROR,
        create_time: new Date().toISOString(),
        update_time: new Date().toISOString(),
        feedback: null,
        conversation_id: conversationId,
        parent_message_id: parentMessageId,
        type: MessageType.RESPONSE,
      };
      setMessages((prev) => [...prev, errorMessage]);
      throw error; // Rethrow error for further handling
    } finally {
      setIsGenerating(false);
      setMessages((prevMessages) => {
        return prevMessages.map((message) => ({
          ...message,
          isGenerating: false,
        }));
      });
      // Clean up AbortController reference
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
    }
  };

  // Handle option selection
  const handleClarificationSelect = async (options: string[]) => {
    if (isGenerating || !conversationId) return;
    await handleSendMessage(options.join(", "));
  };

  const handleGetMessages = async (conversationId: string) => {
    try {
      const response = await conversationApi.getMessages(conversationId);
      if (response.status && response.payload) {
        const apiResponse = response as unknown as ApiResponse<
          ListResponsePayload<ApiMessage>
        >;
        const messages = apiResponse.payload.items;
        if (messages && messages.length > 0) {
          const historyMessages = messages
            .filter((msg) => msg.message.content !== null)
            .map((msg) => mapApiMessageToChatMessage(msg));

          historyMessages.sort(
            (a, b) =>
              new Date(a.create_time).getTime() -
              new Date(b.create_time).getTime(),
          );
          setMessages(historyMessages);
        } else {
          setMessages([]);
        }
      }
    } catch (error) {
      console.error("Failed to load conversation messages:", error);
      setMessages([]);
    }
  };

  const handleGetRoadmap = async (conversationId: string) => {
    try {
      const roadmap_response = await conversationApi.getRoadmap(conversationId);
      if (roadmap_response.status && roadmap_response.payload) {
        const roadmap = (
          roadmap_response as unknown as ApiResponse<RoadMapDataProps>
        ).payload;
        if (roadmap) {
          setRoadmapData(roadmap);
        } else {
          setRoadmapData(null);
        }
      }
    } catch (error) {
      console.error("Failed to load conversation roadmap:", error);
      setRoadmapData(null);
    }
  };
  const handleGetCurConversation = async (conversationId: string) => {
    try {
      const response = await conversationApi.getConversation(conversationId);
      if (response.status && response.payload) {
        setCurrentConversation(response.payload);
        setChatMode(response.payload?.chat_mode || ChatModeType.GENERAL);
      }
    } catch (error) {
      console.error("Failed to load conversation:", error);
    }
  };
  const handleSendMessage = async (
    directMessage?: string,
    describe?: string,
    roadmap?: RoadMapMessage | null,
    files?: string | string[],
  ) => {
    const messageContent = directMessage || input.trim();
    if (!messageContent) return;
    const currentInput = messageContent.trim();
    if (!messageContent && !filePreview.length) return;
    // Get all successfully uploaded file IDs
    let fileIds = filePreview
      .filter((file) => file.status === "success" && file.id)
      .map((file) => file.id);
    if (ScrollToBottomButtonRef.current) {
      ScrollToBottomButtonRef.current?.scrollToBottom("auto");
    }
    isAtBottom.current = true;
    let targetConversationId = state.conversationId;
    // Create user message
    const createUserMessage = (convId: string): Message => ({
      id: Date.now().toString(),
      role: MessageRole.USER,
      content: describe || messageContent,
      status: MessageState.FINISHED,
      create_time: new Date().toISOString(),
      update_time: new Date().toISOString(),
      feedback: null,
      conversation_id: convId,
      parent_message_id: "",
      type: MessageType.USER,
      files: filePreview
        .filter((file) => file.status === "success")
        .map((file) => ({
          filename: file.name,
          size: parseInt(file.size),
          url: `/api/v1/files/${file.id}/preview`,
        })),
      roadmap: roadmap || null,
    });
    setInput("");
    setFilePreview([]);
    setIsGenerating(true);
    setTaskId("");
    setShowRoadmapSelectBtn(false);
    try {
      if (!conversationId) {
        try {
          const conversationName = currentInput.slice(0, 30);
          targetConversationId = await createNewConversation(
            conversationName,
            describe || currentInput,
            chatMode,
          );
          setState({ conversationId: targetConversationId });
        } catch (error) {
          message.error("Failed to create conversation");
          console.error("Failed to create conversation:", error);
        }
      }
      // Create and add user message
      const userMessage = createUserMessage(targetConversationId);
      if (files) {
        try {
          const promptFiles = await getPromptFile(files);
          if (promptFiles?.length) {
            fileIds = promptFiles.map((item) => item.id);
            setMessages((prev) => [
              ...(prev || []),
              { ...userMessage, files: promptFiles },
            ]);
          } else {
            setMessages((prev) => [...(prev || []), userMessage]);
          }
        } catch (error) {
          setMessages((prev) => [...(prev || []), userMessage]);
        }
      } else {
        setMessages((prev) => [...(prev || []), userMessage]);
      }
      setIsThinking(true);
      setThinkingConversationId(targetConversationId);
      await sendMessageWithHandling(
        targetConversationId,
        describe || currentInput,
        userMessage.id,
        fileIds, // Pass all file IDs
        roadmap,
      );
    } catch (error) {
      setIsGenerating(false);
      resetThinkingState();
    }
  };
  const handleSelectConversation = async (conversation: Conversation) => {
    try {
      if (conversation.id === conversationId) return;
      if (isGenerating || isThinking) stopGenerating(); // Stop if message is being generated
      setCurrentConversation(conversation);
      setChatMode(conversation.chat_mode || ChatModeType.GENERAL);
      setState({ conversationId: conversation.id });
      setMessages([]);
      setShowRoadmapSelectBtn(false);
      setShowRoadmapEditBtn(false);
      await handleGetMessages(conversation.id);
      await handleGetRoadmap(conversation.id);
    } catch (error) {
      console.error("Failed to load conversation messages and plan:", error);
    }
  };
  const setNewConversation = () => {
    if (isGenerating || isThinking) stopGenerating();
    setState({ conversationId: undefined });
    setCurrentConversation(null);
    setChatMode(ChatModeType.GENERAL);
    setMessages([]);
    setRoadmapData(null);
    setShowRoadmapSelectBtn(false);
    setShowRoadmapEditBtn(false);
  };

  const stopGenerating = () => {
    // Use AbortController to cancel request, don't call stopChat API
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsGenerating(false);
      resetThinkingState();
      setTaskId("");
    }
    // if (isGenerating && conversationId && taskId) {
    //   conversationApi.stopChat(conversationId, taskId).then((res) => {
    //     if (res.status === true) {
    //       setIsGenerating(false);
    //       setIsThinking(false);
    //       setThinkingConversationId(null);
    //       setTaskId("");
    //     }
    //   });
    // }
  };
  const items: TabsProps["items"] = [
    {
      label: "Agent Workspace",
      key: "1",
      children: <Workspace />,
    },
    {
      label: "Roadmap",
      key: "roadmap",
      children: (
        <Roadmap
          data={roadmapData}
          conversationId={conversationId}
          editable={showRoadmapEditBtn}
          onSave={(data) => {
            const diffRoadmap: RoadMapMessage = {
              previous: roadmapData,
              current: data,
            };
            setShowRoadmapEditBtn(false);
            setShowRoadmapSelectBtn(false);
            handleSendMessage(roadmapUpdateQuery, "", diffRoadmap);
            setRoadmapData(data);
          }}
        />
      ),
    },
    {
      label: "Sandbox",
      key: "3",
      children: <SandBox sandboxUrl={currentConversation?.sandbox_url || ""} />,
    },
  ];
  return (
    <div className={styles.home}>
      <LoginModal />
      <Sidebar
        onSelectConversation={handleSelectConversation}
        setNewConversation={setNewConversation}
        conversationId={conversationId}
      />
      {!conversationId && (
        <div className={styles.newContainer}>
          <section className={styles.newChatSection}>
            <WelcomeView />
            <ChatInput
              setFilePreview={setFilePreview}
              handleSendMessage={handleSendMessage}
              chatMode={chatMode}
              filePreview={filePreview}
            />
            <ChatMode chatModeValue={chatMode} setChatModeValue={setChatMode} />
            <Prompts
              handleSendMessage={handleSendMessage}
              chatMode={chatMode}
            />
          </section>
        </div>
      )}
      {conversationId && (
        <div className={styles.rightContents}>
          <ChatHeader
            currentConversation={currentConversation}
            languageType={languageType}
            setLanguageType={setLanguageType}
            setCurrentConversation={setCurrentConversation}
          />
          <div className={styles.container}>
            <section className={styles.chatSection}>
              <div className={styles.chatContent}>
                <div className={styles.messageArea}>
                  <ScrollToBottomButton
                    className={styles.scrollWrapper}
                    autoScrollThreshold={5}
                    ref={ScrollToBottomButtonRef}
                  >
                    <MessageList
                      messages={messages}
                      onClarificationSelect={handleClarificationSelect}
                      isThinking={
                        isThinking && thinkingConversationId === conversationId
                      }
                      isGenerating={isGenerating}
                      ScrollToBottomButtonRef={ScrollToBottomButtonRef}
                      currentConversationId={conversationId}
                      startTimer={startTimer}
                    />
                    {showRoadmapSelectBtn && (
                      <RoadmapButton
                        setShow={setShowRoadmapSelectBtn}
                        handleSendMessage={handleSendMessage}
                        startTimer={startTimer}
                        setShowRoadmapEditBtn={setShowRoadmapEditBtn}
                      />
                    )}
                  </ScrollToBottomButton>
                </div>
                <ChatInput
                  setFilePreview={setFilePreview}
                  handleSendMessage={handleSendMessage}
                  isGenerating={isGenerating}
                  value={input}
                  setValue={setInput}
                  stopGenerating={stopGenerating}
                  taskId={taskId}
                  chatMode={chatMode}
                  filePreview={filePreview}
                />
              </div>
            </section>
            <section className={styles.workspaceSection}>
              <Tabs
                className={styles.tabSpace}
                defaultActiveKey="1"
                items={items}
                activeKey={activeKey}
                onChange={setActiveKey}
                type="segmented"
              />
            </section>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat;
