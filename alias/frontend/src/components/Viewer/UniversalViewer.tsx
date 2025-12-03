import React from "react";
import { getFileType, languageMap } from "./utils";
import { HtmlViewer } from "./HtmlViewer";
import { MarkdownViewer } from "./MarkdownViewer";
import { CodeViewer } from "./CodeViewer";
import { CSVViewer } from "./CSVViewer";
import { ChartViewer } from "./ChartViewer";
import { DiffViewer } from "./DiffViewer";
import { ViewerStyle } from "./types";

interface UniversalViewerProps {
  content: string;
  fileName?: string;
  style?: ViewerStyle;
}

export const UniversalViewer: React.FC<UniversalViewerProps> = ({
  content,
  fileName = "",
  style = {},
}) => {
  const getViewer = () => {
    const defaultStyles = {
      width: "100%",
      height: "100%",
      overflow: "auto",
      ...style,
    };

    const fileType = fileName?.split(".").pop()?.toLowerCase() || "";
    const type = getFileType(fileType);
    switch (type) {
      case "html":
        return <HtmlViewer content={content} style={defaultStyles} />;

      case "markdown":
        return <MarkdownViewer content={content} style={defaultStyles} />;

      case "csv":
        return <CSVViewer content={content} style={defaultStyles} />;

      //   case 'pdf':
      //     return <PDFViewer content={content} style={defaultStyles} />;

      //   case 'image':
      //     return <ImageViewer content={content} style={defaultStyles} />;

      case "chart":
        return <ChartViewer content={content} style={defaultStyles} />;

      case "diff":
        return <DiffViewer content={content} style={defaultStyles} />;

      default:
        const language = languageMap[fileType] || "text";
        return (
          <CodeViewer
            content={content}
            language={language}
            style={defaultStyles}
          />
        );
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flex: 1,
        // maxHeight: '500px',
        position: "relative",
        // overflow: 'auto',
        // border: '1px solid #ddd',
        borderRadius: "4px",
      }}
    >
      {getViewer()}
    </div>
  );
};
