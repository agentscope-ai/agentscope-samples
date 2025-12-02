const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const FILE_IDS_STORAGE_KEY = "conversation_file_ids";

enum STORAGE_KEY {
  CONVERSATION_ID = "current_conversation_id",
  CONVERSATION = "current_conversation",
}
enum LANGUAGETYPE {
  en_US = "en-US",
  zh_Hans = "zh-Hans",
}
enum ChatModeType {
  GENERAL = "general",
  BROWSER = "browser",
  DEEPREASONING = "dr",
  FINANCE = "finance",
  DATASCIENCE = "ds",
}
const markdownRegex = /^```markdown\n([\s\S]*?)```$/;
const codeBlockRegex = /^```\n([\s\S]*?)```$/;
const ChatModeList = [
  {
    value: ChatModeType.GENERAL,
    label: "General",
  },
  {
    value: ChatModeType.BROWSER,
    label: "Browser Use",
  },
  {
    value: ChatModeType.DEEPREASONING,
    label: "Deep Research",
  },
  {
    value: ChatModeType.FINANCE,
    label: "Financial Analysis",
  },
  {
    value: ChatModeType.DATASCIENCE,
    label: "Data Science",
  },
];
export {
  MAX_FILE_SIZE,
  FILE_IDS_STORAGE_KEY,
  STORAGE_KEY,
  LANGUAGETYPE,
  ChatModeType,
  ChatModeList,
  markdownRegex,
  codeBlockRegex,
};
