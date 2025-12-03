import { fileApi } from "@/services/api/file";
import { ApiMessage } from "@/types/api";
import {
  FeedbackType,
  Message,
  MessageRole,
  MessageState,
  MessageType,
  SelectionType,
  ToolIconType,
} from "@/types/message";
import { MAX_FILE_SIZE } from "@/utils/constant";
import { message } from "@agentscope-ai/design";
const sampleFiles = import.meta.glob("@/assets/file/*");
// Map API message to chat message
const mapApiMessageToChatMessage = (
  msg: ApiMessage,
  generating: boolean = false,
): Message => {
  const baseMessage = {
    ...msg?.message,
    id: msg.id,
    role:
      msg.message.role === "user" ? MessageRole.USER : MessageRole.ASSISTANT,
    content: msg.message.content,
    status: msg.message.status as MessageState,
    create_time: msg.create_time,
    update_time: msg.update_time,
    feedback: msg.feedback
      ? msg.feedback === "like"
        ? FeedbackType.LIKE
        : FeedbackType.DISLIKE
      : null,
    conversation_id: msg.conversation_id,
    parent_message_id: msg.parent_message_id || "",
    isGenerating: generating,
    meta_data: msg.meta_data,
    task_id: msg.task_id,
  };

  // Return directly if it's a user message
  if (msg.message.role === "user") {
    return {
      ...baseMessage,
      type: MessageType.USER,
    };
  }

  // Determine agent message type
  switch (msg.message.type) {
    case "response":
      return {
        ...baseMessage,
        type: MessageType.RESPONSE,
      };
    case "thought":
      return {
        ...baseMessage,
        type: MessageType.THOUGHT,
      };
    case "sub_response":
      return {
        ...baseMessage,
        type: MessageType.SUB_RESPONSE,
      };
    case "sub_thought":
      return {
        ...baseMessage,
        type: MessageType.SUB_THOUGHT,
      };
    case "tool_call":
      return {
        ...baseMessage,
        type: MessageType.TOOL_CALL,
        name: msg.message.name || "",
        arguments: msg.message.arguments || {},
        icon: (msg.message.icon as ToolIconType) || ToolIconType.TOOL,
        content: msg.message.content,
        tool_name: msg.message.tool_name || "",
      };
    case "tool_use":
      return {
        ...baseMessage,
        type: MessageType.TOOL_USE,
        name: msg.message.name || "",
        arguments: msg.message.arguments || {},
        icon: (msg.message.icon as ToolIconType) || ToolIconType.TOOL,
        content: msg.message.content,
        tool_name: msg.message.tool_name || "",
      };
    case "tool_result":
      return {
        ...baseMessage,
        type: MessageType.TOOL_RESULT,
        name: msg.message.name || "",
        arguments: msg.message.arguments || {},
        icon: (msg.message.icon as ToolIconType) || ToolIconType.TOOL,
        content: msg.message.content,
        tool_name: msg.message.tool_name || "",
      };
    case "clarification":
      return {
        ...baseMessage,
        type: MessageType.CLARIFICATION,
        options: msg.message.options || [],
        selection_type:
          msg.message.selection_type === "multiple"
            ? SelectionType.MULTIPLE
            : SelectionType.SINGLE,
      };
    case "files":
      return {
        ...baseMessage,
        type: MessageType.FILES,
        files: msg.message.files || [],
      };
    default:
      return {
        ...baseMessage,
        type: MessageType.RESPONSE,
      };
  }
};

const getPromptFile = async (files: string | string[]) => {
  try {
    const filePaths = Object.keys(sampleFiles);
    if (filePaths.length === 0) {
      console.warn("No files found in assets/file directory");
      return null;
    }
    const paths = Array.isArray(files) ? files : [files];
    const selectedFilePaths = filePaths.filter((filePath) =>
      paths.includes(filePath),
    );

    if (selectedFilePaths.length === 0) {
      console.warn("No matching files found for paths:", paths);
      return null;
    }
    const fileProcessingPromises = selectedFilePaths.map(
      async (selectedFilePath) => {
        try {
          const fileName = selectedFilePath.split("/").pop() || "sample.csv";
          const response = await fetch(selectedFilePath);
          if (!response.ok) {
            console.warn(
              `Failed to fetch file: ${response.status} ${response.statusText}`,
            );
            return null;
          }
          const blob = await response.blob();
          const file = new File([blob], fileName, { type: blob.type });

          if (file.size > MAX_FILE_SIZE) {
            message.error(`File ${file.name} exceeds 10MB limit`);
            return null;
          }

          const uploadResponse: any = await fileApi.uploadFile(file);
          if (uploadResponse?.status && uploadResponse?.payload) {
            const { filename, id, size } = uploadResponse.payload;
            return {
              filename,
              size,
              url: `/api/v1/files/${id}/preview`,
              id,
            };
          }
          return null;
        } catch (fileError) {
          console.warn(
            `Failed to process file ${selectedFilePath}:`,
            fileError,
          );
          return null;
        }
      },
    );
    const results = await Promise.all(fileProcessingPromises);
    const fileResults = results.filter((result) => result !== null);
    return fileResults.length > 0 ? fileResults : null;
  } catch (error) {
    console.error("Failed to load or upload sample files:", error);
    throw error;
  }
};

export { getPromptFile, mapApiMessageToChatMessage };
