import { useTheme } from "@/context/ThemeContext";
import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, prism } from "react-syntax-highlighter/dist/esm/styles/prism"; // Use more modern theme
import { BaseViewerProps } from "./types";

interface CodeViewerProps extends BaseViewerProps {
  language: string;
  title?: string;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  content,
  language,
  title,
  style,
}) => {
  const { theme } = useTheme();
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "fit-content", // Changed to adaptive height
        // backgroundColor: '#282c34', // Match oneDark theme
        borderRadius: "4px",
        ...style,
      }}
    >
      {title && (
        <div
          style={{
            padding: "8px 16px",
            borderBottom: "1px solid #3e4451",
            color: "#abb2bf",
            fontSize: "14px",
            fontFamily: "monospace",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{title}</span>
          <span style={{ opacity: 0.7 }}>{language}</span>
        </div>
      )}
      <div style={{ overflow: "auto" }}>
        <SyntaxHighlighter
          language={language}
          style={theme === "dark" ? oneDark : prism}
          showLineNumbers={true}
          wrapLines={true}
          customStyle={{
            borderTopRightRadius: 0,
            borderTopLeftRadius: 0,
            // maxHeight: 500,
            overflow: "auto",
            background: theme === "dark" ? "" : "transparent",
          }}
          // lineNumberStyle={{
          //   minWidth: '3em',
          //   paddingRight: '1em',
          //   color: '#495162',
          //   textAlign: 'right',
          // }}
        >
          {content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};
