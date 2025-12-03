// src/viewers/MarkdownViewer.ts
import React from "react";
import { BaseViewerProps } from "./types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { markdownRegex } from "@/utils/constant";

export const MarkdownViewer: React.FC<BaseViewerProps> = ({
  content,
  style,
}) => {
  const processed = content?.match(markdownRegex)?.[1] || content;
  return (
    <div style={style}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{processed}</ReactMarkdown>
    </div>
  );
};
