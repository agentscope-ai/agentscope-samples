import { MessageType } from "./message";
import { RoadMap, RoadMapDataProps } from "./roadmap";
import { ChatModeType } from "@/utils/constant";

export interface CreateConversationResponse {
  name: string;
  description: string;
  runtime_status: string;
  create_time: string;
  update_time: string;
  artifacts_sio: string;
  browser_ws: string;
  user_id: string;
  id: string;
  runtime_token: string;
  shared?: boolean;
  sandbox_url?: string;
  chat_mode?: ChatModeType;
}

export interface MessageContent {
  name: string | null;
  role: "user" | "assistant";
  status: string;
  type: MessageType | string;
  content: string | any;
  files?: any[];
  options?: string[];
  selection_type?: "single" | "multiple";
  arguments?: Record<string, any>;
  icon?: string | null;
  tool_name?: string | null;
}

export interface Conversation {
  id: string;
  name: string;
  description: string;
  runtime_status: string;
  create_time: string;
  update_time: string;
  artifacts_sio: string;
  browser_ws: string;
  user_id: string;
  runtime_token: string;
  collected?: boolean;
  shared?: boolean;
  sandbox_url?: string;
  chat_mode?: ChatModeType;
}

export interface ApiMessage {
  message: MessageContent;
  create_time: string;
  update_time: string;
  feedback: "like" | "dislike" | null;
  conversation_id: string;
  parent_message_id: string | null;
  id: string;
  meta_data: FeedbackContentProps;
  task_id: string;
  collected?: boolean;
}

export interface SSEResponse {
  task_id: string;
  conversation_id: string;
  message_id: string;
  runtime_id: string;
  data: {
    messages: ApiMessage[];
    roadmap: RoadMapDataProps;
  };
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
  order_by?: string;
  order_direction?: "asc" | "desc";
}

export interface ListResponsePayload<T> {
  total: number;
  items: T[];
}

export interface ApiResponse<T> {
  status: boolean;
  message: string;
  payload: T;
}

export type ListResponse<T> = ApiResponse<ListResponsePayload<T>>;

export interface StopChatResponse {
  task_id: string;
  conversation_id: string;
}

export interface RuntimeResponse {
  runtime_id: string;
}

export interface DeleteConversationResponse {
  conversation_id: string;
}
export interface Register {
  email: string;
  username: string;
  avatar?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  create_time: Date | string;
  update_time: Date | string;
  last_login_time?: Date | string | null;
  last_login_ip?: string | null;
  id: string;
  has_password: boolean;
  access_token?: string;
  refresh_token?: string;
}

export interface FilesShareResponse {
  id: string;
  status: boolean;
}

export interface UploadFilePayload {
  filename: string;
  mime_type: string;
  extension: string;
  size: number;
  storage_path: string;
  storage_type: string;
  create_time: string;
  update_time: string;
  user_id: string;
  id: string;
  shared: boolean;
}

export interface ConversationFilesPayload {
  total: number;
  items: FileInfo[];
}

export interface ConversationFilesResponse
  extends ApiResponse<ConversationFilesPayload> {}

export interface UploadFileResponse extends ApiResponse<UploadFilePayload> {}

export interface FilePreview {
  name: string;
  type: string;
  size: string;
  id: string;
  status: "uploading" | "success" | "error";
  progress?: number;
  abortController?: AbortController;
}

export interface FileInfo {
  filename: string;
  mime_type: string;
  extension: string;
  size: number;
  storage_path: string;
  storage_type: string;
  create_time: string;
  update_time: string;
  shared: boolean;
  user_id: string;
  id: string;
}

export interface FileResponse {
  status: boolean;
  message: string;
  payload: FileInfo;
}

export interface DeleteFileResponse {
  status: boolean;
  message: string;
  payload: {
    file_id: string;
  };
}

export interface ShareFileRequest {
  share: boolean;
}

export interface NotificationProps {
  message: string;
  visible: boolean;
}
export interface FeedbackContentProps {
  score?: number;
  comment?: string;
  allFeedback?: string[];
  selectedFeedback?: string[];
  mode?: string;
  previous?: RoadMap;
  current?: RoadMap;
}
export interface ConversationFeedbackParams {
  type: string;
  task_id?: string;
  message_id?: string;
  content: FeedbackContentProps;
}
export interface FeedbackConversationPropos {
  conversationId: string;
  taskId: string;
  messageId?: string;
}
export interface FeedbackConversationParams {
  type?: string;
  message_id?: string;
  task_id?: string;
}
export interface ShareConversationsProps {
  name: string;
  description: string;
  runtime_status: string;
  create_time: string;
  update_time: string;
  username: string;
  messages?: ApiMessage[];
  roadmap?: RoadMap;
}
