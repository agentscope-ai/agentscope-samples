import React, { useState, useEffect, ReactNode } from "react";
import { BaseViewerProps } from "./types";

export const HtmlViewer: React.FC<BaseViewerProps> = ({ content, style }) => {
  const [component, setComponent] = useState<ReactNode>(null);

  useEffect(() => {
    setComponent(
      <div
        style={{
          width: "100%",
          height: "100%",
          position: "relative",
          overflow: "hidden",
          ...style,
        }}
      >
        <iframe
          srcDoc={content}
          width="100%"
          height="100%"
          style={{
            border: "none",
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
          }}
        />
      </div>,
    );
  }, [content]);

  return (
    <div
      style={{
        display: "flex",
        flex: 1,
        height: 500,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {component}
    </div>
  );
};
