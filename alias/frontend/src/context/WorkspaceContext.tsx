import {
  createContext,
  Dispatch,
  ReactNode,
  SetStateAction,
  useContext,
  useState,
} from "react";
import { Message } from "@/types/message";
interface WorkspaceContextType {
  displayedContent: string | null;
  args: Record<string, any>;
  setDisplayedContent: Dispatch<SetStateAction<string | null>>;
  setArgs: Dispatch<SetStateAction<Record<string, any>>>;
  activeKey: string;
  setActiveKey: Dispatch<SetStateAction<string>>;
  messageList: Message[];
  setMessageList: Dispatch<SetStateAction<Message[]>>;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [displayedContent, setDisplayedContent] = useState<string | null>(null);
  const [args, setArgs] = useState<Record<string, any>>({});

  const [activeKey, setActiveKey] = useState("1");
  const [messageList, setMessageList] = useState<Message[]>([]);
  return (
    <WorkspaceContext.Provider
      value={{
        displayedContent,
        setDisplayedContent,
        activeKey,
        setActiveKey,
        args,
        setArgs,
        messageList,
        setMessageList,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
}
