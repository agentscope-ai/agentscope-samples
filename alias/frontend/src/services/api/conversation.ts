import {
  ApiMessage,
  ApiResponse,
  Conversation,
  ConversationFeedbackParams,
  ConversationFilesResponse,
  CreateConversationResponse,
  DeleteConversationResponse,
  FeedbackConversationParams,
  FilesShareResponse,
  ListResponse,
  PaginationParams,
  RuntimeResponse,
  ShareConversationsProps,
  SSEResponse,
  StopChatResponse,
} from "@/types/api";
import { RoadMap, RoadMapDataProps, RoadMapMessage } from "@/types/roadmap";
import { ChatModeType, LANGUAGETYPE } from "@/utils/constant";
import { request } from "./request";

export const conversationApi = {
  create: (name: string, description: string, chatMode: string) => {
    return request.post<CreateConversationResponse>("/api/v1/conversations", {
      name,
      description,
      chat_mode: chatMode,
    });
  },
  getConversation: (conversationId: string) => {
    return request.get<Conversation>(`/api/v1/conversations/${conversationId}`);
  },
  sendMessage: (
    conversationId: string,
    message: string,
    onMessage: (data: SSEResponse) => void,
    onError?: (error: any) => void,
    chat_type: string = "task",
    files: string[] = [],
    language_type: string = LANGUAGETYPE.en_US,
    chatMode: ChatModeType = ChatModeType.GENERAL,
    abortController?: AbortController,
    roadmap?: RoadMapMessage | null,
  ) => {
    const requestBody = {
      query: message,
      files: files,
      chat_type: chat_type,
      language_type,
      chat_mode: chatMode,
      roadmap,
    };

    return request.stream(
      `/api/v1/conversations/${conversationId}/chat`,
      onMessage,
      onError,
      requestBody,
      abortController,
    );
  },

  stopChat: (conversationId: string, taskId: string) => {
    return request.post<StopChatResponse>(
      `/api/v1/conversations/${conversationId}/chat/${taskId}/stop`,
    );
  },

  list: (params?: PaginationParams) => {
    return request.get<ListResponse<Conversation>>("/api/v1/conversations", {
      params,
    });
  },

  startRuntime: (conversationId: string) => {
    return request.post<RuntimeResponse>(
      `/api/v1/conversations/${conversationId}/runtime/start`,
    );
  },

  getRuntime: (conversationId: string) => {
    return request.get<RuntimeResponse>(
      `/api/v1/conversations/${conversationId}/runtime`,
    );
  },

  getMessages: (conversationId: string, params?: PaginationParams) => {
    return request.get<ListResponse<ApiMessage>>(
      `/api/v1/conversations/${conversationId}/messages`,
      { params },
    );
  },

  getRoadmap: (conversationId: string) => {
    return request.get<ApiResponse<RoadMap>>(
      `/api/v1/conversations/${conversationId}/roadmap`,
    );
  },

  setRoadmap: (conversationId: string, roadMap: RoadMapDataProps) => {
    return request.post<ApiResponse<RoadMapDataProps>>(
      `/api/v1/conversations/${conversationId}/roadmap`,
      roadMap,
    );
  },

  delete: (conversationId: string) => {
    return request.delete<DeleteConversationResponse>(
      `/api/v1/conversations/${conversationId}`,
    );
  },

  filesShare: (conversationId: string, filePath: string) => {
    return request.post<FilesShareResponse>(
      `/api/v1/conversations/${conversationId}/files/share`,
      {
        filename: filePath,
        share: true,
      },
    );
  },

  getFiles: (conversationId: string) => {
    return request.get<ConversationFilesResponse>(
      `/api/v1/conversations/${conversationId}/files`,
    );
  },

  collect: (conversationId: string, collect: boolean) => {
    return request.post(`/api/v1/conversations/${conversationId}/collect`, {
      collect,
    });
  },
  feedback: (messageId: string, feedback: string | null) => {
    return request.post(`/api/v1/messages/${messageId}/feedback`, { feedback });
  },

  conversationFeedback: (
    conversationId: string,
    params: ConversationFeedbackParams,
  ) => {
    return request.post(
      `/api/v1/conversations/${conversationId}/feedback`,
      params,
    );
  },
  getConversationFeedback: (
    conversationId: string,
    params?: FeedbackConversationParams,
  ) => {
    return request.get(`/api/v1/conversations/${conversationId}/feedback`, {
      params,
    });
  },
  updateConversationName: (conversationId: string, name: string) => {
    return request.post(`/api/v1/conversations/${conversationId}/name`, {
      name,
    });
  },

  shareConversations: (conversationId: string, share: boolean) => {
    return request.post(`/api/v1/conversations/${conversationId}/share`, {
      share,
    });
  },

  getShareConversations: (userId: string, conversationId: string) => {
    return request.get<ShareConversationsProps>(
      `/api/v1/share/conversations/${userId}/${conversationId}`,
    );
  },
};
