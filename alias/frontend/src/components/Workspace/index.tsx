import { useTheme } from "@/context/ThemeContext";
import { useWorkspace } from "@/context/WorkspaceContext.tsx";
import { Message, MessageType, ToolCallMessage } from "@/types/message";
import { Collapse, CollapseProps, Select } from "@agentscope-ai/design";
import { SparkComputerLine } from "@agentscope-ai/icons";
import type { SelectProps } from "antd";
import { memo, useEffect, useMemo, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, prism } from "react-syntax-highlighter/dist/esm/styles/prism";
import { UniversalViewer } from "../Viewer";
import styles from "./index.module.scss";

const Workspace = () => {
  const {
    displayedContent,
    args,
    messageList = [],
    setDisplayedContent,
  } = useWorkspace();
  const { theme } = useTheme();
  const [serialNum, setSerialNum] = useState<number>(0);
  const [useToolInfo, setUseToolInfo] = useState<{
    name: string;
    arguments: string;
    type: string;
  }>({ name: "", arguments: "", type: "" });
  type LabelRender = SelectProps["labelRender"];
  const updateToolInfo = (toolMsg?: ToolCallMessage) => {
    if (
      toolMsg &&
      toolMsg.arguments &&
      Object.keys(toolMsg.arguments).length > 0
    ) {
      setUseToolInfo({
        name: toolMsg.tool_name || "",
        arguments: JSON.stringify(toolMsg.arguments, null, 2),
        type: toolMsg.type,
      });
    } else {
      setUseToolInfo({
        name: "",
        arguments: "",
        type: "",
      });
    }
  };

  useEffect(() => {
    if (displayedContent) {
      const selectedMessage = messageList.find(
        (msg: Message) => msg.content === displayedContent,
      );
      if (selectedMessage) {
        findIndex(selectedMessage.id);
        if ((selectedMessage as ToolCallMessage).arguments) {
          const toolMsg = selectedMessage as ToolCallMessage;
          updateToolInfo(toolMsg);
        } else {
          updateToolInfo(); // Set to null
        }
      }
    } else {
      updateToolInfo(); // Set to null
    }
  }, [displayedContent, messageList]);

  const customStyle = {
    borderTopRightRadius: 0,
    borderTopLeftRadius: 0,
    // maxHeight: 500,
    overflow: "auto",
    padding: 0,
    backgroundColor: "var(--sps-color-bg-base)",
  };
  const renderMarkdown = (content: string, language: string = "text") => {
    return (
      <SyntaxHighlighter
        language={language}
        showLineNumbers={true}
        wrapLines={true}
        style={theme === "dark" ? oneDark : prism}
        customStyle={theme === "dark" ? customStyle : { ...customStyle }}
      >
        {content}
      </SyntaxHighlighter>
    );
  };
  const findIndex = (v: string) => {
    const index = messageList.findIndex((item) => item.id === v);
    setSerialNum(index >= 0 ? index + 1 : 0);
  };
  const getBaseLabel = () => {
    if (!!displayedContent && typeof displayedContent === "string") {
      const displayedContentObj = JSON.parse(displayedContent);
      if (
        Array.isArray(displayedContentObj) &&
        displayedContentObj.length > 0
      ) {
        if (displayedContentObj[0].type === MessageType.TOOL_USE)
          return "Raw data";
        if (displayedContentObj[0].type === MessageType.TOOL_RESULT)
          return "Tool result";
      }
      if (displayedContentObj.hasOwnProperty("type")) {
        if (displayedContentObj.type === MessageType.TOOL_USE)
          return "Raw data";
        if (displayedContentObj.type === MessageType.TOOL_RESULT)
          return "Tool result";
      }
    }
    return "Raw result";
  };
  // Create an array that refreshes each time displayedContent changes
  const items: CollapseProps["items"] = useMemo(() => {
    const base: CollapseProps["items"] = [];
    if (displayedContent === null) {
      return [];
    }
    const currentMessage = messageList.find(
      (msg: Message) => msg.content === displayedContent,
    );
    if (currentMessage) {
      findIndex(currentMessage.id);
    }
    base.push({
      key: "1",
      label: getBaseLabel(),
      children: (
        <SyntaxHighlighter
          language="JSON"
          showLineNumbers={true}
          wrapLines={true}
          style={theme === "dark" ? oneDark : prism}
          // Background color change
          customStyle={
            theme === "dark"
              ? customStyle
              : { ...customStyle, background: "transparent" }
          }
        >
          {(() => {
            try {
              return JSON.stringify(JSON.parse(displayedContent), null, 2);
            } catch (error) {
              return displayedContent;
            }
          })()}
        </SyntaxHighlighter>
      ),
    });

    try {
      const toolResultBlocks = JSON.parse(displayedContent);
      if (Array.isArray(toolResultBlocks)) {
        const toolResultBlock = toolResultBlocks[0];
        if (
          toolResultBlock.hasOwnProperty("name") &&
          toolResultBlock.hasOwnProperty("output")
        ) {
          const { name, output } = toolResultBlock;
          // show output 0 for temp
          switch (name) {
            case "edit_file":
              base.unshift({
                key: "output-0",
                label: `Output of 🛠️ ${name}`,
                children: (
                  <UniversalViewer
                    content={output[0].text}
                    fileName="fake.diff"
                    style={customStyle}
                  />
                ),
              });
              return base;
            case "read_file":
              base.unshift({
                key: "output-0",
                label: `Output of 🛠️ ${name}`,
                children: (
                  <UniversalViewer
                    content={output[0].text}
                    fileName={args?.path}
                    style={customStyle}
                  />
                ),
              });

              return base;
            case "write_file":
              base.unshift({
                key: "output-0",
                label: `Output of 🛠️ ${name}`,
                children: (
                  <UniversalViewer
                    content={args?.content || output[0].text}
                    fileName={args?.path}
                    style={customStyle}
                  />
                ),
              });
              return base;
            case "generate_chart":
              base.unshift({
                key: "output-0",
                label: `Output of 🛠️ ${name}`,
                children: (
                  <UniversalViewer
                    content={output[0].text}
                    fileName="fake.chart"
                    style={customStyle}
                  />
                ),
              });
              return base;
          }

          if (Array.isArray(output)) {
            output.forEach((item, index) => {
              if (item.hasOwnProperty("type")) {
                switch (item.type) {
                  case "text":
                    if (base[0].key === "image") {
                      // Insert at second position
                      base.splice(1, 0, {
                        key: `output-${index}`,
                        label: `Output of 🛠️ ${name}`,
                        children: renderMarkdown(item.text),
                      });
                    } else {
                      base.unshift({
                        key: `output-${index}`,
                        label: `Output of 🛠️ ${name}`,
                        children: renderMarkdown(item.text),
                      });
                    }
                    break;
                  case "image":
                    base.unshift({
                      key: `image-${index}`,
                      label: "Image",
                      children: (
                        <img
                          src={"data:image/jpeg;base64," + item.data}
                          alt="Image"
                          style={{
                            maxWidth: "100%",
                            maxHeight: 500,
                            overflow: "auto",
                          }}
                        />
                      ),
                    });
                    break;
                }
              }
            });
          }
        }
      }
      if (
        useToolInfo.arguments &&
        useToolInfo.name &&
        useToolInfo.type === MessageType.TOOL_USE
      ) {
        base.unshift({
          key: "input",
          label: `Arguments of 🛠️ ${useToolInfo.name}`,
          children: renderMarkdown(useToolInfo.arguments),
        });
      }
    } catch (error) {}

    return base;
  }, [displayedContent, args, theme, useToolInfo]);

  const selectOnchange = (v: string) => {
    // v is now id, need to find corresponding message based on id
    const selectedMessage = messageList.find((msg: Message) => msg.id === v);
    if (selectedMessage && selectedMessage.content !== displayedContent) {
      findIndex(v);
      setDisplayedContent(selectedMessage.content);
      // Find corresponding message and set arguments
      if ((selectedMessage as ToolCallMessage).arguments) {
        const toolMsg = selectedMessage as ToolCallMessage;
        updateToolInfo(toolMsg);
      } else {
        updateToolInfo(); // Set to null
      }

      setTimeout(() => {
        const element = document.getElementById(
          `message-toolcall-${selectedMessage.id}`,
        );
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 100);
    }
  };
  const renderLabel = (d: ToolCallMessage | Message) => {
    let prefixName = `Output of `;
    if (d?.type === MessageType.TOOL_USE) prefixName = `Using tool input of `;
    if (d?.type === MessageType.TOOL_RESULT)
      prefixName = `Tool result output of `;
    return (
      <div className={styles.renderLabel}>
        <span> {`${prefixName}🛠️ ${d?.tool_name ?? "Unknown Tool"}`}</span>
        <span className={styles.labelId}>{d.id}</span>
      </div>
    );
  };
  const labelRender: LabelRender = (props) => {
    const { value } = props;
    // Find corresponding message based on value (id)
    const message = messageList.find((msg: Message) => msg.id === value);
    if (!message) {
      return <span>No option match</span>;
    }
    const d = message as ToolCallMessage;
    let prefixName = `Output of `;
    if (d?.type === MessageType.TOOL_USE) prefixName = `Using tool input of `;
    if (d?.type === MessageType.TOOL_RESULT)
      prefixName = `Tool result output of `;
    return <span>{`${prefixName}🛠️ ${d?.tool_name ?? "Unknown Tool"}`}</span>;
  };
  return (
    <div className={styles.workWrap}>
      <div className={styles.workspaceHeader}>
        <div className={styles.titleContainer}>
          <SparkComputerLine className={styles.computerIcon} />
          <h2 className={styles.title}>Agent Workspace</h2>
        </div>
      </div>
      {displayedContent && (
        <div className={styles.todoHeader}>
          <span className={styles.stepTitle}>
            <Select
              className={styles.workspaceSelect}
              prefix={
                <span className={styles.stepCount}>
                  {serialNum}/{messageList?.length}
                </span>
              }
              value={
                messageList.find(
                  (msg: Message) => msg.content === displayedContent,
                )?.id
              }
              onChange={(v) => {
                selectOnchange(v);
              }}
              notFoundContent={null}
              options={(messageList || []).map((d: Message) => ({
                value: d.id,
                label: renderLabel(d),
                // disabled: displayedContent === null
              }))}
              labelRender={labelRender}
            />
          </span>
        </div>
      )}

      <div className={styles.todoList}>
        {displayedContent ? (
          <Collapse
            items={items}
            className={styles.collapse}
            defaultActiveKey={
              items.length === 1 ? ["1"] : ["file", "output", "image"]
            }
          />
        ) : null}
      </div>
    </div>
  );
};

export default memo(Workspace);
