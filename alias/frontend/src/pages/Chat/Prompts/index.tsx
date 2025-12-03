import { originalPromptsList, promptJson } from "@/assets/json/prompt";
import { RoadMapMessage } from "@/types/roadmap";
import { ChatModeList, ChatModeType } from "@/utils/constant";
import { Button, Card } from "@agentscope-ai/design";
import {
  SparkAiEditLine,
  SparkAiNoteLine,
  SparkBehavioralInsightLine,
  SparkChatAnywhereLine,
  SparkMagicWandLine,
  SparkReplaceLine,
  SparkReplayLine,
  SparkRoboticsLine,
} from "@agentscope-ai/icons";
import { Col, Flex, Row } from "antd";
import { debounce } from "lodash";
import React, { memo, useCallback, useEffect, useMemo, useState } from "react";
import styles from "./index.module.scss";
interface PromptsProps {
  handleSendMessage: (
    value?: string,
    description?: string,
    roadmap?: RoadMapMessage | null,
    files?: string | string[],
  ) => void;
  chatMode: ChatModeType;
}
interface PromptsModeProps {
  title: string;
  describe: string;
  files?: string[] | string;
  icon?: React.ReactNode;
}

const PromptCard: React.FC<{ item: PromptsModeProps }> = ({ item }) => {
  const [isHovered, setIsHovered] = useState(false);
  return (
    <Card
      className={styles.promptsCard}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Flex vertical gap={12}>
        {item.icon}
        <div className={styles.promptsName}>{item.title}</div>
        <div className={styles.promptsDesc}>{item.describe}</div>
        {isHovered && (
          <Button type="primary" className={styles.promptsButton}>
            Run Agent
          </Button>
        )}
      </Flex>
    </Card>
  );
};

// Icon array
const icons = [
  <SparkReplayLine className={styles.promptsIcon} />,
  <SparkRoboticsLine className={styles.promptsIcon} />,
  <SparkMagicWandLine className={styles.promptsIcon} />,
  <SparkAiNoteLine className={styles.promptsIcon} />,
  <SparkAiEditLine className={styles.promptsIcon} />,
  <SparkChatAnywhereLine className={styles.promptsIcon} />,
  <SparkBehavioralInsightLine className={styles.promptsIcon} />,
];

const Prompts: React.FC<PromptsProps> = ({ handleSendMessage, chatMode }) => {
  const fontSize = { fontSize: 18 };
  // Get corresponding prompt list from promptJson based on chatMode
  const modeSpecificPrompts = useMemo(() => {
    const currentMode = ChatModeList.find((mode) => mode.value === chatMode);
    const modeKey = currentMode?.value || ChatModeType.GENERAL;
    const promptsForMode: PromptsModeProps[] =
      promptJson[modeKey] || promptJson[ChatModeType.GENERAL] || [];
    return promptsForMode.length > 0 ? promptsForMode : originalPromptsList;
  }, [chatMode]);

  useEffect(() => {
    handleChangePrompts();
  }, [chatMode]);

  // Function to generate random prompt items, ensuring no duplicates with previous ones
  const generateRandomPrompts = useCallback(
    (previousPrompts: any[] = []) => {
      // Get indices of previous prompt items
      const previousIndices = previousPrompts
        .map((prompt) =>
          modeSpecificPrompts.findIndex(
            (item: PromptsModeProps) => item.title === prompt.title,
          ),
        )
        .filter((index) => index !== -1);

      // Filter out unused prompt items
      const availableIndices = [
        ...Array(modeSpecificPrompts.length).keys(),
      ].filter((index) => !previousIndices.includes(index));

      // Use all items if available items are less than 2
      const indicesToUse =
        availableIndices.length >= 2
          ? availableIndices
          : [...Array(modeSpecificPrompts.length).keys()];

      // Randomly select two different indices
      const shuffledIndices = indicesToUse
        .sort(() => 0.5 - Math.random())
        .slice(0, Math.min(2, modeSpecificPrompts.length)); // Ensure not exceeding available count

      // Assign non-duplicate icons to each selected prompt
      const selectedIcons = [...icons];

      return shuffledIndices.map((index) => {
        // Randomly select one from remaining icons
        const randomIconIndex = Math.floor(
          Math.random() * Math.min(selectedIcons.length, icons.length),
        );
        const icon = selectedIcons[randomIconIndex];

        // Remove used icons from available icons to ensure no duplicates
        if (selectedIcons.length > 1) {
          selectedIcons.splice(randomIconIndex, 1);
        }

        return {
          ...modeSpecificPrompts[index],
          icon,
        };
      });
    },
    [modeSpecificPrompts],
  );

  // Use state to manage random prompt items
  const [randomPrompts, setRandomPrompts] = useState<PromptsModeProps[]>(() =>
    generateRandomPrompts(),
  );

  // Function to update random prompt items
  const handleChangePrompts = useCallback(() => {
    setRandomPrompts((prevPrompts) => generateRandomPrompts(prevPrompts));
  }, [generateRandomPrompts]);

  const debouncedHandleSendMessage = useCallback(
    debounce(
      (
        title: string,
        describe: string,
        roadmap: RoadMapMessage | null,
        files: string | string[] | undefined,
      ) => {
        handleSendMessage(title, describe, roadmap, files);
      },
      300,
    ),
    [handleSendMessage],
  );
  return (
    <div className={styles.prompts}>
      <Flex align="center" justify="space-between" className={styles.header}>
        <div>Starting from these cases</div>
        <Flex
          gap="middle"
          onClick={handleChangePrompts}
          style={{ cursor: "pointer" }}
        >
          <SparkReplaceLine style={fontSize} />
          Change it
        </Flex>
      </Flex>
      <Row gutter={[16, 16]}>
        {randomPrompts.map((item, index) => {
          return (
            <Col
              span={12}
              key={item.title}
              onClick={() => {
                if (item.title)
                  debouncedHandleSendMessage(
                    item.title,
                    item.describe,
                    null,
                    item.files,
                  );
              }}
            >
              <PromptCard item={item} />
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

export default memo(Prompts);
