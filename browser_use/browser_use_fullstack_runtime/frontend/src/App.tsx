import React, { useState, useRef, useEffect } from "react"; // 添加 useEffect
import { Layout, theme } from "antd";

import { Input, List } from "antd";
import type { InputRef } from "antd";

import { Image, Avatar, Spin } from "antd";
import { Flex } from "antd";

const { Content, Footer } = Layout;

const REACT_APP_API_URL =
  process.env.REACT_APP_API_URL || "http://localhost:9000";
const BACKEND_URL = REACT_APP_API_URL + "/v1/chat/completions";
const BACKEND_DESLKTOP_URL = REACT_APP_API_URL + "/env_info";
const DEFAULT_MODEL = "qwen-max";
const systemMessage = {
  role: "system",
  content: "You are a helpful assistant.",
};

type SiteItem = {
  title: string;
  url: string;
  favicon: string;
  description: string;
};
type ChatMessage = {
  message: string;
  think: string;
  sender: string;
  site: SiteItem[];
}[];
const { Search } = Input;

const App: React.FC = () => {
  const inputRef = useRef<InputRef>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [desktopUrl, setDesktopUrl] = useState("");
  const handleFocus = () => {
    if (inputRef.current) {
      inputRef.current.select();
    }
  };
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();
  const [messages, setMessages] = useState<ChatMessage>([
    {
      message: "Hello, I'm the assistant! Ask me anything!",
      sender: "assistant",
      think: "",
      site: [],
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);

  async function get_desktop_url() {
    const response = await fetch(BACKEND_DESLKTOP_URL, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    if (!response.body) {
      throw new Error("ReadableStream not found in response.");
    }

    const data = await response.json();
    console.log(data);
    setDesktopUrl(data.url);
  }

  const handleSend = async (message: string) => {
    await get_desktop_url();
    setCollapsed(true);
    if (message.trim() === "") {
      return;
    }
    const newMessage = {
      message,
      sender: "user",
      think: "",
      site: [],
    };

    const newMessages = [...messages, newMessage];

    setMessages(newMessages);

    setIsTyping(true);

    await processMessageToChatGPT(newMessages);
    await get_desktop_url();
  };

  async function processMessageToChatGPT(chatMessages: ChatMessage) {
    const apiMessages = chatMessages
      .map((messageObject) => {
        if (messageObject.message.trim() === "") {
          return null;
        }
        const role =
          messageObject.sender === "assistant" ? "assistant" : "user";
        return { role, content: messageObject.message };
      })
      .filter(Boolean);

    const apiRequestBody = {
      model: DEFAULT_MODEL,
      messages: [systemMessage, ...apiMessages],
      stream: true,
    };

    const response = await fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(apiRequestBody),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    if (!response.body) {
      throw new Error("ReadableStream not found in response.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedMessage = "";
    setMessages([
      ...chatMessages,
      {
        message: "",
        sender: "assistant",
        think: "",
        site: [],
      },
    ]);
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      const chunk = decoder.decode(value);
      accumulatedMessage += chunk;

      const lines = accumulatedMessage.split("\n");
      accumulatedMessage = lines.pop() || "";

      for (const line of lines) {
        if (line.trim() === "") {
          continue;
        }

        try {
          const parsed = JSON.parse(line.split("data: ")[1]);
          const content = parsed.choices[0]?.delta?.content || "";
          if (content) {
            setMessages((prevMessages) => [
              ...prevMessages.slice(0, -1),
              {
                ...prevMessages[prevMessages.length - 1],
                message:
                  prevMessages[prevMessages.length - 1].message + content,
                sender: "assistant",
                site: [],
              },
            ]);
          }
        } catch (error) {
          console.error("Error parsing JSON:", error);
        }
      }
    }

    setIsTyping(false);
  }

  useEffect(() => {
    const scrollInterval = setInterval(() => {
      if (listRef.current) {
        listRef.current.scrollTop = listRef.current.scrollHeight;
      }
    }, 1000);

    return () => clearInterval(scrollInterval);
  }, [messages]);

  return (
    <Layout
      style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}
    >
      <Content style={{ padding: "0 48px", flex: 1 }}>
        <div
          style={{
            background: colorBgContainer,
            minHeight: 600,
            padding: 24,
            borderRadius: borderRadiusLG,
          }}
        >
          <Flex vertical={true} gap={"large"}>
            <Flex gap={"large"} style={{ marginBottom: 30 }}>
              <Image
                width={48}
                src="logo512.png"
                onClick={() => {
                  window.location.reload();
                }}
                style={{ cursor: "pointer" }}
              />
              <Search
                ref={inputRef}
                placeholder=""
                allowClear
                enterButton="Search"
                size="large"
                onSearch={handleSend}
                onFocus={handleFocus}
              />
            </Flex>
            <Flex gap={"large"}>
              <Flex vertical={true} style={{ width: 500 }} gap={"large"}>
                {collapsed && (
                  <List
                    size="large"
                    bordered
                    dataSource={messages.slice(1)}
                    style={{ color: "black" }}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              src={
                                item.sender === "user"
                                  ? "user_avatar.svg"
                                  : "logo512.png"
                              }
                            />
                          }
                          title={item.sender}
                          description={item["message"]}
                        />
                        {isTyping && item === messages[messages.length - 1] && (
                          <Spin />
                        )}
                      </List.Item>
                    )}
                  />
                )}
              </Flex>

              {desktopUrl && (
                <iframe
                  src={desktopUrl}
                  style={{ width: "1280px", height: "800px", border: "none" }}
                  title="DesktopPage"
                />
              )}
            </Flex>
          </Flex>
        </div>
      </Content>
      <Footer style={{ textAlign: "center" }}></Footer>
    </Layout>
  );
};

export default App;
