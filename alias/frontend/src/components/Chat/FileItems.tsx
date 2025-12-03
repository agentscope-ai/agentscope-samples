import iconDoc from "@/assets/icons/files/doc.svg";
import iconFile from "@/assets/icons/files/file.svg";
import iconHtml from "@/assets/icons/files/html.svg";
import iconImage from "@/assets/icons/files/image.svg";
import iconPdf from "@/assets/icons/files/pdf.svg";
import iconXml from "@/assets/icons/files/xml.svg";
import { FileItem } from "@/types/message";
import { formatFileSize } from "@/utils/fileNameUtils";
import React from "react";
import { useLocation, useParams } from "react-router-dom";

import styles from "./Message.module.scss";

interface FileItemsProps {
  files: FileItem[];
}

const getFileIcon = (filename: string) => {
  if (!filename) return iconFile;
  const ext = filename.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "jpg":
      return iconImage;
    case "jpeg":
      return iconImage;
    case "png":
      return iconImage;
    case "gif":
      return iconImage;
    case "pdf":
      return iconPdf;
    case "doc":
      return iconDoc;
    case "docx":
      return iconDoc;
    case "html":
      return iconHtml;
    case "xml":
      return iconXml;
    default:
      return iconFile;
  }
};

const getFileTypeText = (filename: string) => {
  if (!filename) return "FILE";
  const ext = filename.split(".").pop()?.toUpperCase();
  if (ext === "XLS" || ext === "XLSX") return "XLS";
  if (ext === "PDF") return "PDF";
  if (ext === "DOC" || ext === "DOCX") return "DOC";
  if (["JPG", "JPEG", "PNG", "GIF"].includes(ext || "")) return "IMG";
  return ext || "FILE";
};

export const FileItems: React.FC<FileItemsProps> = ({ files }) => {
  const location = useLocation();
  const isSharePage = location.pathname.includes("/share/");
  const { sessionId, userId } = useParams<{
    userId: string;
    sessionId: string;
  }>();
  if (!files || !Array.isArray(files) || files.length === 0) {
    return null;
  }
  const handlePreview = (file: FileItem) => {
    if (!file.id) return;

    const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
    // const endpoint = isSharePage ? "public" : "preview";
    // const url = `${baseUrl}/api/v1/files/${file.id}/${endpoint}`;
    let url: string;
    if (isSharePage && userId && sessionId) {
      url = `${baseUrl}/api/v1/share/conversations/${userId}/${sessionId}/files/${file.id}/public`;
    } else {
      url = `${baseUrl}/api/v1/files/${file.id}/preview`;
    }
    // If not share page, need to add authentication header
    if (!isSharePage) {
      const token =
        localStorage.getItem("access_token") ||
        import.meta.env.VITE_API_ACCESS_TOKEN ||
        import.meta.env.VITE_API_TOKEN;
      if (!token) {
        console.error("No access token available");
        return;
      }

      // Create a request with authentication header
      fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((response) => response.blob())
        .then((blob) => {
          const objectUrl = URL.createObjectURL(blob);
          window.open(objectUrl, "_blank");
          // Clean up URL
          setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        })
        .catch((error) => {
          console.error("Failed to preview file:", error);
        });
    } else {
      // Share page opens link directly
      window.open(url, "_blank");
    }
  };

  return (
    <>
      {files.map((file, index) => (
        <div key={index} className={styles.fileItem}>
          <div className={styles.fileLeft}>
            <img
              src={getFileIcon(file?.filename || "")}
              className={styles.fileIcon}
              alt="file icon"
            />
          </div>
          <div className={styles.fileInfoBlock}>
            <div className={styles.fileName} title={file?.filename}>
              {file?.filename || "Unknown file"}
            </div>
            <div className={styles.fileSize}>
              {getFileTypeText(file?.filename || "")}{" "}
              {formatFileSize(file?.size || 0)}
            </div>
          </div>
          {file?.id && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handlePreview(file);
              }}
              className={styles.downloadBtn}
            >
              Preview
            </button>
          )}
        </div>
      ))}
    </>
  );
};
