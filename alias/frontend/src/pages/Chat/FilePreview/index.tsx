import { FileItems } from "@/components/Chat/FileItems";
import { fileApi } from "@/services/api/file";
import { FilePreview as filePreviewItem } from "@/types/api";
import { FILE_IDS_STORAGE_KEY } from "@/utils/constant";
import {
  getStoredFileIds,
  removeFileIds,
  saveFileIds,
} from "@/utils/fileNameUtils";
import { message } from "@agentscope-ai/design";
import { SparkFalseLine } from "@agentscope-ai/icons";
import React, { memo, useState } from "react";
import styles from "./index.module.scss";

interface FilePreviewProps {
  filePreview: filePreviewItem[];
  setFilePreview: React.Dispatch<React.SetStateAction<filePreviewItem[]>>;
  conversationId: string;
}
const FilePreview: React.FC<FilePreviewProps> = ({
  filePreview,
  setFilePreview,
  conversationId,
}) => {
  const [localFileList, setLocalFileList] = useState<Set<string>>(new Set());
  const handleRemoveFile = async (fileName: string) => {
    const fileToRemove = filePreview.find((fp) => fp.name === fileName);
    if (!fileToRemove) return;

    // Cancel upload if file is being uploaded
    if (fileToRemove.status === "uploading" && fileToRemove.abortController) {
      fileToRemove.abortController.abort();
      return;
    }

    // Delete file if it has been uploaded successfully
    if (fileToRemove.id) {
      try {
        await fileApi.deleteFile(fileToRemove.id);
        setFilePreview((prev) => prev.filter((fp) => fp.name !== fileName));

        // Remove from local file list
        setLocalFileList((prev) => {
          const newSet = new Set(prev);
          newSet.delete(fileName);
          return newSet;
        });

        // Remove file ID from local storage
        if (conversationId) {
          const currentIds = getStoredFileIds(
            FILE_IDS_STORAGE_KEY,
            conversationId,
          );
          const newIds =
            currentIds.filter((id) => id !== fileToRemove.id) || [];
          if (newIds && newIds?.length > 0)
            saveFileIds(FILE_IDS_STORAGE_KEY, conversationId, newIds);
          if (newIds?.length === 0)
            removeFileIds(FILE_IDS_STORAGE_KEY, conversationId);
        }

        message.success(`File ${fileName} deleted`);
      } catch (error) {
        console.error("Failed to delete file:", error);
        message.error(`Failed to delete file ${fileName}, please try again`);
      }
    } else {
      // Remove directly from preview list if file upload failed or was not successful
      console.log("File has no ID, removing directly from list");
      setFilePreview((prev) => prev.filter((fp) => fp.name !== fileName));
    }
  };

  return (
    <>
      {filePreview.length > 0 && (
        <div className={styles.filePreviewContainer}>
          {filePreview.map((file, index) => (
            <div key={index} className={styles.filePreviewItem}>
              <FileItems
                files={[
                  {
                    filename: file.name,
                    size: parseInt(file.size),
                    url: file.id
                      ? `/api/v1/files/${file.id}/preview`
                      : undefined,
                  },
                ]}
              />
              <div className={styles.fileBottom}>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${file.progress || 0}%` }}
                  />
                </div>
                <div className={styles.fileStatus}>
                  {file.status === "uploading" && (
                    <span className={styles.uploading}>Uploading...</span>
                  )}
                  {file.status === "success" && (
                    <span className={styles.success}>Upload successful</span>
                  )}
                  {file.status === "error" && (
                    <span className={styles.error}>Upload failed</span>
                  )}
                  <button
                    className={styles.removeButton}
                    onClick={() => handleRemoveFile(file.name)}
                    title="Remove file"
                  >
                    <SparkFalseLine />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
};

export default memo(FilePreview);
