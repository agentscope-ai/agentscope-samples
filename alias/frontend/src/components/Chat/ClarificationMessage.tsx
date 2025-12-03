import {
  ClarificationMessage as ClarificationType,
  SelectionType,
} from "@/types/message";
import React, { useState } from "react";
import styles from "./Message.module.scss";

interface ClarificationMessageProps {
  message: ClarificationType;
  onSelect?: (options: string[]) => void;
}

export const ClarificationMessage: React.FC<ClarificationMessageProps> = ({
  message,
  onSelect,
}) => {
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);

  const handleOptionClick = (option: string) => {
    if (message.selection_type === SelectionType.SINGLE) {
      setSelectedOptions([option]);
      onSelect?.([option]);
    } else {
      const newSelection = selectedOptions.includes(option)
        ? selectedOptions.filter((item) => item !== option)
        : [...selectedOptions, option];
      setSelectedOptions(newSelection);
    }
  };

  const handleConfirm = () => {
    if (
      message.selection_type === SelectionType.MULTIPLE &&
      selectedOptions.length > 0
    ) {
      onSelect?.(selectedOptions);
    }
  };

  return (
    // <BaseMessage message={message} onFeedback={onFeedback}>
    <div className={styles.clarificationMessage}>
      {message.content && (
        <div className={styles.question}>{message.content}</div>
      )}
      {Array.isArray(message?.options) && message.options.length > 0 && (
        <div className={styles.options}>
          {message.options?.map((option, index) => (
            <button
              key={index}
              className={`${styles.option} ${
                selectedOptions.includes(option) ? styles.selected : ""
              }`}
              onClick={(e) => {
                e.stopPropagation();
                handleOptionClick(option);
              }}
              disabled={
                selectedOptions.length > 0 && !selectedOptions.includes(option)
              }
            >
              {option}
            </button>
          ))}
        </div>
      )}
      {message.selection_type === SelectionType.MULTIPLE && (
        <button
          className={styles.confirmButton}
          onClick={handleConfirm}
          disabled={selectedOptions.length === 0}
        >
          Confirm
        </button>
      )}
    </div>
    // {/* </BaseMessage> */}
  );
};
