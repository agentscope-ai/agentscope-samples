import React, { ReactNode, useEffect, useState } from "react";
import { BaseViewerProps } from "./types";

export interface DiffLine {
  line: string;
  type: "addition" | "deletion" | "info" | "context";
}

export const DiffViewer: React.FC<BaseViewerProps> = ({ content, style }) => {
  const [component, setComponent] = useState<ReactNode>(null);

  useEffect(() => {
    // Parse diff content
    const parseDiff = (content: string): DiffLine[] => {
      // Remove diff markers and file information
      const cleanDiffContent = (raw: string) => {
        return raw
          .trim() // First clean leading and trailing whitespace
          .replace(/^```diff\n|\n```$/g, "") // Remove markdown diff markers
          .replace(/\\n/g, "\n") // Replace escaped newlines
          .replace(/\\"/g, '"') // Replace escaped quotes
          .replace(/\n+$/, "") // Remove trailing newlines
          .trimEnd(); // Finally clean trailing whitespace
      };
      const diffContent = cleanDiffContent(content);

      // show all lines
      const lines = diffContent.split("\n").filter(
        (line) => true,
        // !line.startsWith('Index:') &&
        // !line.startsWith('===')
        // !line.startsWith('---') &&
        // !line.startsWith('+++')
      );

      return lines.map((line) => {
        const type = line.startsWith("+")
          ? "addition"
          : line.startsWith("-")
          ? "deletion"
          : line.startsWith("@")
          ? "info"
          : "context";

        return { line, type };
      });
    };

    const diffLines = parseDiff(content);

    setComponent(
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          overflow: "auto",
          fontFamily: "monospace",
          fontSize: "14px",
          // backgroundColor: '#282c34',
          color: "#abb2bf",
          ...style,
        }}
      >
        {diffLines.map((item, index) => (
          <div
            key={index}
            style={{
              display: "flex",
              backgroundColor:
                item.type === "addition"
                  ? "rgba(40, 167, 69, 0.2)"
                  : item.type === "deletion"
                  ? "rgba(203, 36, 49, 0.2)"
                  : item.type === "info"
                  ? "rgba(88, 96, 105, 0.2)"
                  : "transparent",
              padding: "2px 10px",
              whiteSpace: "pre",
            }}
          >
            <span
              style={{
                color:
                  item.type === "addition"
                    ? "#28a745"
                    : item.type === "deletion"
                    ? "#cb2431"
                    : item.type === "info"
                    ? "#586069"
                    : "#abb2bf",
              }}
            >
              {item.line}
            </span>
          </div>
        ))}
      </div>,
    );
  }, [content, style]);

  return (
    <div
      style={{
        display: "flex",
        flex: 1,
        // maxHeight: 500,
        position: "relative",
        overflow: "auto",
        // border: '1px solid #ddd',
        borderRadius: "4px",
      }}
    >
      {component}
    </div>
  );
};
