export interface Conversation {
  id: string;
  name: string;
  description?: string;
  status: "running" | "stopped";
  create_time: string;
  update_time: string;
  user_id: string;
  browser_ws: string;
  artifacts_sio: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  name?: string;
  create_time: string;
  update_time: string;
  feedback?: "like" | "dislike";
  conversation_id: string;
  parent_message_id?: string;
}

export interface CreateConversationRequest {
  name?: string;
  description?: string;
}

export interface ChatRequest {
  query: string;
  files?: string[];
}

export interface PaginationRequest {
  page?: number;
  page_size?: number;
  order_by?: string;
  order_direction?: "asc" | "desc";
}

export interface PaginationResponse<T> {
  total: number;
  items: T[];
}

export interface ApiResponse<T> {
  status: boolean;
  message: string;
  payload: T;
}

export interface ChatResponse {
  task_id: string;
  conversation_id: string;
  message_id: string;
  runtime_id: string;
  data: {
    content: string;
  };
}
