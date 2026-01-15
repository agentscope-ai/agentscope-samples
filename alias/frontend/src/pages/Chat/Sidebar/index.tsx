import LogoIcon from "@/components/LogoIcon";
import { useMessage } from "@/context/MessageContext";
import { useTheme } from "@/context/ThemeContext";
import { useWorkspace } from "@/context/WorkspaceContext";
import { conversationApi } from "@/services/api/conversation";
import { loginApi } from "@/services/api/login";
import type { ApiResponse, ListResponsePayload } from "@/types/api";
import { Conversation } from "@/types/api";
import { HistoryPanel } from "@agentscope-ai/chat";
import { AlertDialog, Button, message, Popover } from "@agentscope-ai/design";
import {
  SparkChatTabFill,
  SparkDeleteLine,
  SparkDownLine,
  SparkEffciencyLine,
  SparkHistoryLine,
  SparkMessageLine,
  SparkMoonLine,
  SparkOperateLeftLine,
  SparkOperateRightLine,
  SparkSocialInteraction01Line,
  SparkSunLine,
  SparkUpLine,
} from "@agentscope-ai/icons";
import classNames from "classnames";
import React, { memo, useEffect, useRef, useState } from "react";
import { Conversation as HistoryConversation } from "@agentscope-ai/chat/lib/Conversations";
import { useNavigate } from "react-router-dom";
import Avatar from "../Avatar";
import HabbitModal from "../Habbit";
import styles from "./index.module.scss";

interface SidebarProps {
  conversationId: string;
  onSelectConversation: (conversation: Conversation) => void;
  setNewConversation: () => void;
}

// History type
type HistoryType = "collected" | "all";

const Sidebar: React.FC<SidebarProps> = ({
  conversationId,
  onSelectConversation,
  setNewConversation,
}) => {
  const { theme, setTheme } = useTheme();
  const { setDisplayedContent, setActiveKey, setArgs, setMessageList } =
    useWorkspace();
  const { setCurrentConversation } = useMessage();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [showList, setShowList] = useState<boolean>(true);
  const [showCollect, setShowCollect] = useState<boolean>(true);
  const [showConversationList, setShowConversationList] = useState(true);
  const [enterLogo, setEnterLogo] = useState<boolean>(false);
  const [showHabbit, setShowHabbit] = useState<boolean>(false);
  const [userInfo, setUserInfo] = useState({
    uid: "",
    userName: "",
    email: "",
  });
  const iconStyle = { fontSize: 20 };
  const isHasFetchedRef = useRef(false);

  const fetchConversations = async () => {
    try {
      const response = await conversationApi.list({
        page: 1,
        page_size: 100,
        order_by: "create_time",
        order_direction: "desc",
      });
      if (response.status && response.payload) {
        const listResponse = response as unknown as ApiResponse<
          ListResponsePayload<Conversation>
        >;
        // Ensure structure matches expected format before accessing
        const payloadItems = listResponse.payload?.items;
        if (Array.isArray(payloadItems)) {
          setConversations(payloadItems);
        } else {
          setConversations([]);
        }
      }
    } catch (error) {
      message.error("Failed to fetch conversation history");
    }
  };

  useEffect(() => {
    if (!isHasFetchedRef.current) {
      loginApi.getUsers().then((res) => {
        setUserInfo({
          uid: res?.payload?.id || "",
          userName: res?.payload?.username || "",
          email: res?.payload?.email || "",
        });
      });
      isHasFetchedRef.current = true;
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [showConversationList]);

  const clearWorkspace = () => {
    setDisplayedContent(null);
    setArgs({});
    setActiveKey("1");
    setMessageList([]);
  };

  const hideHistory = () => {
    setShowConversationList(false);
    onMouseOutLogo();
  };

  const goChatDetails = (convId: string) => {
    if (convId === conversationId) return;
    clearWorkspace();
    const conv = conversations.find((item) => item.id === convId);
    if (conv) {
      onSelectConversation(conv);
      setCurrentConversation(conv);
      hideHistory();
    }
  };

  const goNewChat = () => {
    onMouseOutLogo();
    clearWorkspace();
    setNewConversation();
    setShowConversationList(false);
  };

  const goHome = () => {
    onMouseOutLogo();
    clearWorkspace();
    setNewConversation();
    setCurrentConversation(null);
    navigate("/");
    setShowConversationList(false);
  };

  const deletedConversation = async (id: string) => {
    AlertDialog.warning({
      title: "Confirm deletion of this conversation?",
      children:
        "Once deleted, it cannot be recovered. Please proceed with caution.",
      centered: true,
      okText: "Confirm deletion",
      onOk: async () => {
        try {
          const reslut = await conversationApi.delete(id);
          if (reslut.status) {
            setConversations(
              conversations.filter((item) => item.id !== id) || [],
            );
            message.success(
              reslut.message || "Conversation deleted successfully",
            );
            if (conversationId === id) goNewChat();
          }
        } catch (error) {
          message.error("Failed to delete conversation");
        }
      },
    });
  };

  const onMouseEnterLogo = () => {
    setEnterLogo(true);
  };

  const onMouseOutLogo = () => {
    setEnterLogo(false);
  };

  const expandSidebar = () => {
    if (!conversationId) {
      setShowConversationList(true);
    }
  };

  // Get delete menu item
  const getDeleteMenuItem = [
    {
      label: "Delete",
      key: "delete",
      icon: <SparkDeleteLine />,
      danger: true,
      onClick: (conv: HistoryConversation) => {
        deletedConversation(conv.key);
      },
    },
  ];

  // Get filtered conversation list
  const getFilteredConversations = (type: HistoryType): Conversation[] => {
    if (type === "collected") {
      return Array.isArray(conversations)
        ? conversations.filter((conv) => conv.collected)
        : [];
    }
    return Array.isArray(conversations)
      ? conversations.filter((conv) => !conv.collected)
      : [];
  };

  // Render history panel
  const renderHistoryPanel = (type: HistoryType, isExpanded: boolean) => {
    const isCollected = type === "collected";
    const filteredConversations = getFilteredConversations(type);
    const showPanel = isCollected ? showCollect : showList;
    const setShowPanel = isCollected ? setShowCollect : setShowList;
    const title = isCollected ? "My Collection" : "History";
    const icon = isCollected ? (
      <SparkSocialInteraction01Line style={iconStyle} />
    ) : (
      <SparkHistoryLine style={iconStyle} />
    );

    // Don't show collection section if there are no collected conversations
    if (isCollected && filteredConversations.length === 0) return null;

    // Show empty state if there are no conversations (only when expanded)
    if (filteredConversations.length === 0) {
      return isExpanded && !isCollected ? (
        <div>No conversation records</div>
      ) : null;
    }

    return (
      <div className={styles.siderBarHistory}>
        {isExpanded ? (
          <>
            <div
              className={styles.sidebarItem}
              onClick={() => setShowPanel(!showPanel)}
            >
              {icon}
              <div className={styles.itemText}>{title}</div>
              {showPanel ? <SparkDownLine /> : <SparkUpLine />}
            </div>

            {showPanel && (
              <HistoryPanel
                menu={getDeleteMenuItem}
                items={filteredConversations.map((item) => ({
                  key: item.id,
                  label: item.name,
                }))}
                onActiveChange={goChatDetails}
                activeKey={conversationId}
              />
            )}
          </>
        ) : (
          <Popover
            placement="rightTop"
            trigger="hover"
            overlayClassName={styles.historyPopover}
            onOpenChange={(open) => open && fetchConversations()}
            content={
              <div className={styles.popoverContent}>
                <div className={styles.popoverHeader}>{title}</div>
                <HistoryPanel
                  menu={getDeleteMenuItem}
                  items={filteredConversations.map((item) => ({
                    key: item.id,
                    label: item.name,
                  }))}
                  onActiveChange={goChatDetails}
                  activeKey={conversationId}
                />
              </div>
            }
          >
            <div className={styles.sidebarItem} title={title}>
              {icon}
            </div>
          </Popover>
        )}
      </div>
    );
  };
  const isExpanded = !conversationId && showConversationList;
  const isHomePage = !conversationId;

  const renderSidebarContent = () => (
    <nav
      className={classNames(styles.sidebar, {
        [styles.collapsed]: !isExpanded,
      })}
    >
      {/* Logo Section */}
      <div className={styles.sidebarLogo}>
        <div
          className={classNames(
            "transition-transform hover:scale-105 w-10 h-10 cursor-pointer relative",
          )}
          onClick={conversationId ? goHome : expandSidebar}
          onMouseEnter={isHomePage ? onMouseEnterLogo : undefined}
          onMouseLeave={isHomePage ? onMouseOutLogo : undefined}
        >
          <LogoIcon
            className={classNames(
              "w-full h-full object-cover transition-opacity",
              {
                "opacity-0": isHomePage && !isExpanded && enterLogo,
              },
            )}
          />
          {/* When on homepage and not expanded, show expand icon on hover, overlay on logo */}
          {isHomePage && !isExpanded && enterLogo && (
            <div
              className="absolute inset-0 flex items-center justify-center cursor-pointer transition-transform hover:scale-105 z-10"
              onClick={(e) => {
                e.stopPropagation();
                expandSidebar();
              }}
            >
              <SparkOperateRightLine style={iconStyle} />
            </div>
          )}
        </div>
        {isExpanded && (
          <div
            className="w-5 h-5 cursor-pointer transition-transform hover:scale-105"
            onClick={hideHistory}
          >
            <SparkOperateLeftLine style={iconStyle} />
          </div>
        )}
      </div>

      {/* Navigation Section */}
      <div className={styles.sidebarNav}>
        <div
          className={classNames(styles.sidebarItem, {
            [styles.active]: !conversationId,
          })}
          onClick={goNewChat}
          title={!isExpanded ? "New Agent Task" : undefined}
        >
          {isHomePage ? (
            <SparkChatTabFill style={iconStyle} />
          ) : (
            <SparkMessageLine style={iconStyle} />
          )}
          <div className={styles.itemText}>New Agent Task</div>
        </div>

        {/* History Sections */}
        {renderHistoryPanel("collected", isExpanded)}
        {renderHistoryPanel("all", isExpanded)}
      </div>

      {/* Footer Section */}
      <div className={styles.sidebarFooter}>
        {isExpanded ? (
          <div className={styles.footerBox}>
            <div className={styles.footerLeft}>
              <Avatar userInfo={userInfo} />
              <div className="ml-2">{userInfo.userName}</div>
            </div>
            <Button
              type="text"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className={styles.iconButton}
            >
              {theme === "dark" ? (
                <SparkMoonLine style={iconStyle} />
              ) : (
                <SparkSunLine style={iconStyle} />
              )}
            </Button>
          </div>
        ) : (
          <>
            <Button
              type="text"
              onClick={() => setShowHabbit(true)}
              className={styles.iconButton}
            >
              <SparkEffciencyLine style={iconStyle} />
            </Button>
            <Button
              type="text"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className={styles.iconButton}
            >
              {theme === "dark" ? (
                <SparkMoonLine style={iconStyle} />
              ) : (
                <SparkSunLine style={iconStyle} />
              )}
            </Button>
            <Avatar userInfo={userInfo} />
          </>
        )}
      </div>
    </nav>
  );

  return (
    <div
      className={classNames(styles.sidebarWrapper, {
        [styles.expanded]: isExpanded,
      })}
    >
      {renderSidebarContent()}
      <HabbitModal
        open={showHabbit}
        setOpen={setShowHabbit}
        uid={userInfo.uid}
      />
    </div>
  );
};

export default memo(Sidebar);
