import { conversationApi } from "@/services/api/conversation";
import { fileApi } from "@/services/api/file";
import { FilePreview } from "@/types/api";
import { ChatModeList, MAX_FILE_SIZE } from "@/utils/constant";
import { formatFileSize, getUniqueFileName } from "@/utils/fileNameUtils";
import {
  Attachments,
  Disclaimer,
  ChatInput as Input,
} from "@agentscope-ai/chat";
import { IconButton, message } from "@agentscope-ai/design";
import { SparkAttachmentLine } from "@agentscope-ai/icons";
import { GetProp, Upload } from "antd";
import React, { memo, useMemo } from "react";
import styles from "./index.module.scss";

// Define file item type
type AttachmentItem = GetProp<typeof Attachments, "items">[number];

interface ChatInputProps {
  handleSendMessage: (value: string) => void;
  setFilePreview: React.Dispatch<React.SetStateAction<FilePreview[]>>;
  setValue?: (value: string) => void;
  value?: string;
  conversationId?: string;
  isGenerating?: boolean;
  stopGenerating?: () => void;
  taskId?: string;
  chatMode: string;
  filePreview: FilePreview[];
}
const createModeLabel = (text: string) => (
  <div className="flex items-center">
    <div className={styles.badge}></div>
    {text}
  </div>
);
const ChatInput: React.FC<ChatInputProps> = ({
  conversationId,
  isGenerating,
  value,
  taskId,
  handleSendMessage,
  setFilePreview,
  setValue,
  stopGenerating,
  chatMode,
  filePreview,
}) => {
  const [attachedFiles, setAttachedFiles] = React.useState<AttachmentItem[]>(
    [],
  );
  const options = useMemo(() => {
    const getChatModeLabel = () => {
      const mode = ChatModeList.find((mode) => mode.value === chatMode);
      return mode ? `${mode.label} · Ready` : "General Mode · Ready";
    };

    return [
      {
        icon: "",
        label: createModeLabel(getChatModeLabel()),
        value: chatMode,
        tooltip: "",
      },
      {
        icon: "",
        label: createModeLabel("Alias is handling the task..."),
        value: "isGenerating",
        tooltip: "",
      },
    ];
  }, [chatMode]);
  const handleCustomRequest = async (options: {
    file: File;
    onSuccess: Function;
    onError: Function;
    onProgress: Function;
  }) => {
    const { file, onSuccess, onError, onProgress } = options;
    try {
      // Merge file names from server file list and local preview list
      let existingFiles: string[] = [];
      if (conversationId) {
        // Get file list for current conversation
        const response: any = await conversationApi.getFiles(conversationId);
        if (!response.status || !response.payload) {
          message.error("Failed to get file list");
          onError(new Error("Failed to get file list"));
          return;
        }
        existingFiles = [
          ...(response.payload.items || []),
          ...attachedFiles.map(
            (fp) => `conversations/${conversationId}/${fp.name}`,
          ),
        ];
      }
      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        message.error(`File ${file.name} exceeds 10MB limit`);
        onError(new Error(`File ${file.name} exceeds 10MB limit`));
        return;
      }

      // Check if this file already exists locally (including files being uploaded)
      const isUploading = attachedFiles.some((fp) => fp.name === file.name);
      if (isUploading) {
        message.error(
          `File ${file.name} is being uploaded, please do not upload again.`,
        );
        onError(
          new Error(
            `File ${file.name} is being uploaded, please do not upload again`,
          ),
        );
        return;
      }

      // Get unique file name
      const uniqueFileName = getUniqueFileName(existingFiles, file.name);
      // Create new File object if file name has changed
      const renamedFile =
        uniqueFileName !== file.name
          ? new File([file], uniqueFileName, { type: file.type })
          : file;

      // Add new file preview
      const newAttachedFiles: AttachmentItem = {
        uid: `temp-${Date.now()}-${file.name}`,
        name: uniqueFileName,
        type: file.type,
        size: file.size,
        status: "uploading",
      };

      const newFilePreview: FilePreview = {
        name: uniqueFileName,
        type: file.type,
        size: formatFileSize(file.size || 0),
        id: "",
        status: "uploading",
        progress: 0,
      };

      setAttachedFiles((prev) => [...prev, newAttachedFiles]);
      setFilePreview((prev) => [...prev, newFilePreview]);

      // Create upload progress callback
      const progressCallback = (progressEvent: ProgressEvent) => {
        const progress = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total,
        );

        // Update progress
        setAttachedFiles((prev) =>
          prev.map((fp) =>
            fp.name === uniqueFileName ? { ...fp, progress } : fp,
          ),
        );

        onProgress({ percent: progress });
      };

      // Execute upload
      const uploadResponse: any = await fileApi.uploadFile(
        renamedFile,
        progressCallback,
      );

      if (uploadResponse.status && uploadResponse.payload) {
        const fileId = uploadResponse.payload.id;
        // Update status to success
        setAttachedFiles((prev) =>
          prev.map((fp) =>
            fp.name === uniqueFileName
              ? {
                  ...fp,
                  uid: fileId,
                  status: "done",
                  progress: 100,
                }
              : fp,
          ),
        );
        setFilePreview((prev) =>
          prev.map((fp) =>
            fp.name === uniqueFileName
              ? {
                  ...fp,
                  id: fileId,
                  status: "success",
                  progress: 100,
                }
              : fp,
          ),
        );
        message.success(`File ${uniqueFileName} uploaded successfully`);
        onSuccess(uploadResponse.payload, file);
      } else {
        // Update status to error
        setAttachedFiles((prev) =>
          prev.map((fp) =>
            fp.name === uniqueFileName
              ? {
                  ...fp,
                  status: "error",
                  progress: 0,
                }
              : fp,
          ),
        );
        setFilePreview((prev) =>
          prev.map((fp) =>
            fp.name === uniqueFileName
              ? {
                  ...fp,
                  status: "error",
                  progress: 0,
                }
              : fp,
          ),
        );
        message.error(`File ${uniqueFileName} upload failed`);
        onError(new Error("Upload failed"));
      }
    } catch (error: any) {
      // Get file name (may have been renamed)
      const fileName = file.name;
      message.error(`File ${fileName} upload failed, please try again`);
      onError(error);
    }
  };
  const handleDeleteFileChange: GetProp<
    typeof Attachments,
    "onChange"
  > = async ({ file, fileList }) => {
    const result = await fileApi.deleteFile(file.uid);
    if (result.status) {
      setAttachedFiles(fileList);
      setFilePreview(filePreview.filter((item) => item.id !== file.uid));
      message.success(`File ${file.name} deleted`);
    }
  };
  const onSubmit = (value: string) => {
    if (value) {
      setAttachedFiles([]);
      setFilePreview([]);
      handleSendMessage(value);
    }
  };
  const senderHeader = (
    <Input.Header closable={false} open={attachedFiles?.length > 0}>
      <Attachments items={attachedFiles} onChange={handleDeleteFileChange} />
    </Input.Header>
  );

  const attachmentsNode = (
    <Upload
      fileList={attachedFiles}
      showUploadList={false}
      key="upload"
      multiple
      maxCount={5}
      customRequest={handleCustomRequest}
    >
      <IconButton icon={<SparkAttachmentLine />} bordered={false} />
    </Upload>
  );
  const onCancel = () => {
    if (stopGenerating) stopGenerating();
  };
  return (
    <div className={styles.chatInput}>
      <Input.ModeSelect
        options={options}
        value={isGenerating ? "isGenerating" : chatMode}
        onChange={() => {}}
      />
      <Input
        placeholder="Please type here..."
        header={senderHeader}
        prefix={[attachmentsNode]}
        loading={isGenerating && taskId ? true : false}
        onSubmit={onSubmit}
        onChange={setValue}
        value={value}
        onCancel={onCancel}
      />
      <Disclaimer desc="AI can also make mistakes. Please use with caution." />
    </div>
  );
};

export default memo(ChatInput);
