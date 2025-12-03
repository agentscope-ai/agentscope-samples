import { useTheme } from "@/context/ThemeContext";
import { Button, Modal, Tooltip } from "@agentscope-ai/design";
import { css } from "@codemirror/lang-css";
import { html } from "@codemirror/lang-html";
import { java } from "@codemirror/lang-java";
import { javascript } from "@codemirror/lang-javascript";
import { markdown } from "@codemirror/lang-markdown";
import { python } from "@codemirror/lang-python";
import { Prec } from "@codemirror/state";
import { keymap } from "@codemirror/view";
import { materialDark, materialLight } from "@uiw/codemirror-theme-material";
import CodeMirror from "@uiw/react-codemirror";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal as XTerm } from "@xterm/xterm";
import { createTwoFilesPatch } from "diff";
import "github-markdown-css/github-markdown-light.css";
import "highlight.js/styles/github-dark.css";
import "katex/dist/katex.min.css";
import React, { memo, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import io, { Socket } from "socket.io-client";
import "xterm/css/xterm.css";
import { classNames } from "../../utils/classNames";
import styles from "./index.module.scss";
import "./index.scss";
import { PanelHeader } from "./PanelHeader";
import { FileTree } from "./Tree";
const DEFAULT_TERMINAL_SIZE = 25;
const DEFAULT_EDITOR_SIZE = 100 - DEFAULT_TERMINAL_SIZE;
// const { DirectoryTree } = Tree;
let socket: Socket;
const darkTheme = {
  background: "#131414",
  foreground: "#ffffff",
  cursor: "#dddddd",
};
const lightTheme = {
  background: "#ffffff",
  foreground: "#333333",
  cursor: "#333333",
};

const Artifacts = (Props: {
  webSocketUrl: { artifactsSio: any };
  runtimeToken: string;
}) => {
  const [fileTree, setFileTree] = useState([]);
  const [codeValue, setCodeValue] = useState("");
  const [extensions, setExtensions] = useState([javascript()]);
  const [fileName, setFileName] = useState("");
  const [markdownValue, setMarkdownValue] = useState("");
  const [htmlModal, setHtmlModal] = useState("");
  const [modal, setModal] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"saved" | "modified" | null>(
    null,
  );
  const [originalContent, setOriginalContent] = useState("");
  const terminalElementRef = useRef<HTMLDivElement>(null);
  const artifactsSio = Props?.webSocketUrl?.artifactsSio;
  const saveTimeoutRef = useRef<NodeJS.Timeout>();
  const runtimeToken = Props?.runtimeToken;
  const fitAddonRef = useRef<FitAddon | null>(null);
  const terminalRef = useRef<XTerm | null>(null);

  const [lastCommand, setLastCommand] = useState("");
  const [isCommandRunning, setIsCommandRunning] = useState(false);
  const [commandOutput, setCommandOutput] = useState("");
  const lastCommandRef = useRef("");
  const { theme } = useTheme();

  // Move handleOutput function to component top
  const handleOutput = (data: string) => {
    if (terminalElementRef.current) {
      const terminal = terminalElementRef.current.querySelector(
        ".xterm",
      ) as any;
      if (terminal && terminal.terminal) {
        terminal.terminal.write(data);
      }
    }
  };

  const getMessage = () => {
    let data: never[] = [];
    try {
      socket = io(artifactsSio, {
        path: "/artifacts/socket.io",
        auth: {
          token: runtimeToken,
        },
      });
    } catch (error) {
      console.error("Failed to connect to WebSocket:", error);
      // Handle connection failures, such as displaying an error message to the user
    }
    // socket = io("http://localhost:4500/artifacts");
    socket.on("connect", () => {
      console.log("Connection successful");
      // Reset all state
      setFileTree([]);
      setCodeValue("");
      setFileName("");
      setMarkdownValue("");
      setHtmlModal("");
      setModal(false);
    });
    socket.on("error", (event) => {
      // Error exception message
      console.log("error", event);
    });
    socket.emit("requestFileList");
    socket.on("fileTree", (fileTree) => {
      setFileTree(fileTree || []);
      data = fileTree;
    });
    return data;
  };
  useEffect(() => {
    getMessage();

    // Add timer to refresh file tree every 3 seconds
    const timer = setInterval(() => {
      if (socket) {
        socket.emit("requestFileList");
      }
    }, 3000);

    // Cleanup function
    return () => {
      clearInterval(timer);
      if (socket) {
        socket.off("connect");
        socket.off("error");
        socket.off("fileTree");
        socket.off("fileContent");
        socket.off("output", handleOutput);
      }
    };
  }, [artifactsSio]);
  const onExpand = (info: { type: string; path: any; name: string }) => {
    if (info?.type !== "file") {
      return;
    }
    const filePath = info?.path;
    socket.emit("loadFile", filePath);
    const handleFileContent = ({
      content,
      path,
    }: {
      content: string;
      path: string;
    }) => {
      setFileName(path);
      detectLanguage(path);
      setCodeValue(content);
      setOriginalContent(content);
      // Clear modification status when switching files
      setSaveStatus(null);
      if (path.split(".").slice(-1)[0] === "md") {
        setMarkdownValue(content);
      }
      if (path.split(".").slice(-1)[0] === "html") {
        setHtmlModal(content);
      }
    };
    socket.on("fileContent", handleFileContent);

    return () => {
      socket.off("fileContent", handleFileContent);
    };
  };

  const langMap = (fileExtension: string | undefined) => {
    let mode = javascript();
    switch (fileExtension) {
      case "css":
        mode = css();
        break;
      case "java":
        mode = java();
        break;
      case "ts":
        mode = javascript();
        break;
      case "js":
        mode = javascript();
        break;
      case "html":
        mode = html();
        break;
      case "py":
        mode = python();
        break;
      case "md":
        mode = markdown();
        break;
    }
    return mode;
  };
  // Language switching

  const detectLanguage = (fileName: string) => {
    const ext = fileName.split(".").slice(-1)[0];
    const langLoader = langMap(ext);
    setExtensions([langLoader]);
  };

  // Save file
  const saveKeymap = Prec.high(
    // Ensure shortcut key priority
    keymap.of([
      {
        key: "Ctrl-s",
        mac: "Cmd-s",
        run: (editor) => {
          saveCurrentFile(fileName);
          return true; // Prevent browser default behavior
        },
      },
    ]),
  );
  const handleCodeChange = (value: string) => {
    setCodeValue(value);
    setSaveStatus("modified");

    // Also update preview content
    const fileExt = fileName.split(".").slice(-1)[0];
    if (fileExt === "md") {
      setMarkdownValue(value);
    } else if (fileExt === "html") {
      setHtmlModal(value);
    }
  };

  const saveCurrentFile = (fileName: string) => {
    if (fileName) {
      socket.emit("saveFile", {
        filename: fileName,
        content: codeValue,
      });
      const diffResult = createTwoFilesPatch(
        fileName,
        fileName,
        originalContent, // Original content
        codeValue, // Current content
      );

      // TODO: push event
      console.warn("diffResult", diffResult);

      // Update original content after successful save
      setOriginalContent(codeValue); // Add this line

      // Clear save status after 3 seconds
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      saveTimeoutRef.current = setTimeout(() => {
        setSaveStatus(null);
      }, 3000);
    }
  };
  // Terminal
  useEffect(() => {
    const element = terminalElementRef.current!;
    const fitAddon = new FitAddon();
    fitAddonRef.current = fitAddon;
    const terminal = new XTerm({
      fontSize: 14,
      fontFamily: 'Consolas, "Courier New", monospace',
      theme: theme === "dark" ? darkTheme : lightTheme,
    });
    // Save terminal instance reference
    terminalRef.current = terminal;
    terminal.loadAddon(fitAddon);
    terminal.open(element);
    fitAddon.fit();

    let currentCommand = "";

    terminal.onData((data) => {
      socket.emit("input", data);
      if (data === "\r" || data === "\n") {
        if (currentCommand.trim()) {
          const command = currentCommand.trim();
          setLastCommand(command);
          lastCommandRef.current = command;
          setIsCommandRunning(true);
          setCommandOutput(""); // Clear previous output
          currentCommand = "";
        }
      } else if (data === "\u007f") {
        // Backspace key
        currentCommand = currentCommand.slice(0, -1);
      } else if (data.length === 1 && data.charCodeAt(0) >= 32) {
        // Printable character
        currentCommand += data;
      }
    });
    const handleOutput = (data: string) => {
      terminal.write(data);

      if (isCommandRunning) {
        setCommandOutput((prev) => {
          const newOutput = prev + data;

          const cleanedOutput = newOutput
            .replace(/\x1b\[[0-9;]*[a-zA-Z]/g, "")
            .replace(/\x1b\][0-9];[^\x07]*\x07/g, "")
            .replace(/\x1b\][0-9];[^\x1b]*\x1b\\/g, "")
            .replace(/\[?\?[0-9]+[hl]/g, ""); // More lenient prompt matching
          const promptPattern = /root@[a-f0-9]+:[^#]*#\s*$/;
          if (promptPattern.test(cleanedOutput)) {
            setIsCommandRunning(false);

            const promptMatch = cleanedOutput.match(
              /root@[a-f0-9]+:[^#]*#\s*$/,
            );
            if (promptMatch) {
              const cleanOutput = cleanedOutput
                .substring(0, promptMatch.index)
                .trim();
              // TODO: push event
              console.warn(
                `Command: ${lastCommandRef.current}\nResults: ${cleanOutput}`,
              );
            }
            return "";
          }
          return newOutput;
        });
      }
    };

    socket.on("output", handleOutput);
    return () => {
      terminal.dispose();
      socket.off("connect");
      socket.off("error");
      socket.off("fileTree");
      socket.off("fileContent");
      socket.off("output", handleOutput);
    };
  }, [artifactsSio]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.options.theme =
        theme === "dark" ? darkTheme : lightTheme;
    }
  }, [theme]);
  const onClose = () => {
    setModal(false);
  };
  const modalTitle = (
    <div className={styles.modalTitle}>
      <span
        style={{
          wordBreak: "break-all",
          maxWidth: "100%",
        }}
      >
        {fileName}
      </span>
      {saveStatus && (
        <span
          className={classNames(styles.saveStatus, {
            [styles.modified]: saveStatus === "modified",
            [styles.saved]: saveStatus === "saved",
          })}
        >
          {saveStatus === "modified" ? "• Modified • Ctrl + S" : "• Saved"}
        </span>
      )}
    </div>
  );
  return (
    <div className={styles.artifactsWrap}>
      <Modal
        title={modalTitle}
        open={modal}
        centered={true}
        // footer={null}
        onCancel={onClose}
        onOk={onClose}
        width={960}
      >
        <div className={styles.modalContent}>
          {fileName.split(".").slice(-1)[0] === "md" ? (
            <div
              className={`markdown-body ${
                theme === "dark" ? "markdown-dark" : "markdown-light"
              }`}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeHighlight, rehypeKatex]}
                components={{
                  code(props: any) {
                    const { node, inline, className, children, ...rest } =
                      props;
                    const match = /language-(\w+)/.exec(className || "");
                    return !inline && match ? (
                      <pre>
                        <code className={match[1]} {...rest}>
                          {children}
                        </code>
                      </pre>
                    ) : (
                      <code className={className} {...rest}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {markdownValue}
              </ReactMarkdown>
            </div>
          ) : fileName.split(".").slice(-1)[0] === "html" ? (
            <div className="iframe-box">
              <iframe
                srcDoc={htmlModal}
                sandbox="allow-scripts"
                style={{
                  width: "100%",
                  height: "100%",
                  border: "none",
                }}
              />
            </div>
          ) : (
            <CodeMirror
              value={codeValue}
              height="500px"
              extensions={[...extensions, saveKeymap]}
              onChange={handleCodeChange}
              theme={theme === "dark" ? materialDark : materialLight}
            />
          )}
        </div>
      </Modal>
      <PanelGroup
        direction="vertical"
        onLayout={() => {
          fitAddonRef.current?.fit();
        }}
      >
        <Panel defaultSize={50} minSize={20}>
          <PanelGroup direction="horizontal">
            <Panel defaultSize={40} minSize={10} collapsible>
              <div
                className="flex flex-col border-r border-bolt-elements-borderColor h-full"
                style={{ backgroundColor: "transparent" }}
              >
                <PanelHeader>Files</PanelHeader>
                <div className={styles.treeWrap}>
                  <FileTree
                    data={fileTree}
                    onExpand={onExpand}
                    show={"noShow"}
                  />
                </div>
              </div>
            </Panel>
            <PanelResizeHandle />
            <Panel className="flex flex-col" defaultSize={80} minSize={20}>
              <PanelHeader className="overflow-x-auto">
                <div className="header">
                  <div className="fileName">
                    <Tooltip title={fileName} placement="top">
                      <span
                        style={{
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {fileName}
                      </span>
                    </Tooltip>

                    {saveStatus && (
                      <span
                        className={classNames(styles.saveStatus, {
                          [styles.modified]: saveStatus === "modified",
                          [styles.saved]: saveStatus === "saved",
                        })}
                      >
                        {saveStatus === "modified"
                          ? "• Modified • Ctrl + S"
                          : "• Saved"}
                      </span>
                    )}
                  </div>
                  {(fileName.split(".").slice(-1)[0] === "md" ||
                    fileName.split(".").slice(-1)[0] === "html") && (
                    <Button
                      type="link"
                      style={{ flexShrink: 0 }}
                      onClick={() => {
                        // Update preview content before opening preview
                        const fileExt = fileName.split(".").slice(-1)[0];
                        if (fileExt === "md") {
                          setMarkdownValue(codeValue);
                        } else if (fileExt === "html") {
                          setHtmlModal(codeValue);
                        }
                        setModal(true);
                      }}
                    >
                      Preview
                    </Button>
                  )}
                </div>
              </PanelHeader>
              <div className={styles.codeWrap}>
                <CodeMirror
                  value={codeValue}
                  extensions={[...extensions, saveKeymap]}
                  theme={theme === "dark" ? materialDark : materialLight}
                  onChange={(value) => {
                    setCodeValue(value);
                    setSaveStatus("modified");
                  }}
                />
              </div>
            </Panel>
          </PanelGroup>
        </Panel>
        <PanelResizeHandle />
        <Panel defaultSize={20} minSize={10}>
          <div className="h-full" style={{ height: "100%" }}>
            <div
              className="bg-bolt-elements-terminals-background h-full flex flex-col"
              style={{ height: "100%" }}
            >
              <div className="flex items-center bg-bolt-elements-background-depth-2 border-y border-bolt-elements-borderColor gap-1.5 min-h-[34px] p-2">
                <React.Fragment>
                  <div
                    className={classNames(
                      "flex items-center text-sm cursor-pointer gap-1.5 px-3 py-2 h-full whitespace-nowrap rounded-full",
                      {
                        "bg-bolt-elements-terminals-buttonBackground text-bolt-elements-textSecondary hover:text-bolt-elements-textPrimary":
                          false,
                        "bg-bolt-elements-background-depth-2 text-bolt-elements-textSecondary hover:bg-bolt-elements-terminals-buttonBackground":
                          !false,
                      },
                    )}
                  >
                    Terminal
                  </div>
                </React.Fragment>
              </div>
              <div className="terminal" ref={terminalElementRef} />
            </div>
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
};
export default memo(Artifacts);
