import { RoadMap, RoadMapMessage } from "./roadmap";
export enum MessageRole {
  USER = "user",
  ASSISTANT = "assistant",
  SYSTEM = "system",
}

export enum FeedbackType {
  LIKE = "like",
  DISLIKE = "dislike",
}

export enum MessageType {
  RESPONSE = "response",
  THOUGHT = "thought",
  SUB_RESPONSE = "sub_response",
  SUB_THOUGHT = "sub_thought",
  TOOL_CALL = "tool_call",
  CLARIFICATION = "clarification",
  FILES = "files",
  USER = "user",
  SYSTEM = "system",
  TOOL_USE = "tool_use",
  TOOL_RESULT = "tool_result",
}

export enum ToolIconType {
  TOOL = "tool",
  BROWSER = "browser",
  FILE = "file",
}

export enum SelectionType {
  SINGLE = "single",
  MULTIPLE = "multiple",
}

export enum MessageState {
  RUNNING = "running",
  WAITING = "waiting",
  FINISHED = "finished",
  ERROR = "error",
}

export interface FileItem {
  filename: string;
  size: number;
  url?: string;
  id?: string;
}

export interface SubMessage {
  type: MessageType;
  content: string | null;
  status: MessageState;
  name?: string | null;
  arguments?: Record<string, any>;
  icon?: string | null;
}

export interface BaseMessage {
  id: string;
  parent_message_id: string;
  parent_id?: string;
  role: MessageRole;
  content: string;
  type: MessageType;
  create_time: string;
  status: MessageState;
  name?: string | null;
  update_time: string;
  feedback: FeedbackType | null;
  conversation_id: string;
  sub_messages?: SubMessage[];
  isGenerating?: boolean;
  meta_data?: any;
  task_id?: string;
  roadmap?: RoadMapMessage | null;
}

export interface ResponseMessage extends BaseMessage {
  type: MessageType.RESPONSE;
}

export interface ThoughtMessage extends BaseMessage {
  type: MessageType.THOUGHT;
}

export interface SubResponseMessage extends BaseMessage {
  type: MessageType.SUB_RESPONSE;
}

export interface SubThoughtMessage extends BaseMessage {
  type: MessageType.SUB_THOUGHT;
}

export interface ToolCallMessage extends BaseMessage {
  type: MessageType.TOOL_CALL | MessageType.TOOL_USE | MessageType.TOOL_RESULT;
  name: string;
  arguments: Record<string, any>;
  icon: ToolIconType;
  tool_name?: string | null;
}

export interface ClarificationMessage extends BaseMessage {
  type: MessageType.CLARIFICATION;
  options: string[];
  selection_type: SelectionType;
}

export interface FilesMessage extends BaseMessage {
  type: MessageType.FILES;
  files: FileItem[];
}

export interface UserMessage extends BaseMessage {
  type: MessageType.USER;
  files?: FileItem[];
}

export interface SystemMessage extends BaseMessage {
  type: MessageType.SYSTEM;
}

export type Message =
  | ResponseMessage
  | ThoughtMessage
  | SubResponseMessage
  | SubThoughtMessage
  | ToolCallMessage
  | ClarificationMessage
  | FilesMessage
  | UserMessage
  | SystemMessage;

export interface SSEMessageResponse {
  task_id: string;
  conversation_id: string;
  message_id: string;
  runtime_id: string;
  data: {
    messages: Message[];
    roadmap: RoadMap;
  };
}
