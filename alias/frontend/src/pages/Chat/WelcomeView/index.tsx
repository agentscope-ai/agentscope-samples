import React, { memo } from "react";
import { Button, Flex } from "antd";
import { Welcome } from "@agentscope-ai/chat";
import { SparkUpperrightArrowLine } from "@agentscope-ai/icons";
import LogoIcon from "@/components/LogoIcon";
import AgentscopeLogoIcon from "@/components/AgentscopeLogoIcon";
import AlisaLogoIcon from "@/components/AlisaLogoIcon";
import styles from "./index.module.scss";
const WelcomeView: React.FC = ({}) => {
  const goGitHub = (url: string) => {
    window.open(url, "_blank");
  };
  return (
    <Flex vertical className={styles.welcome}>
      <div className={styles.githubButton}>
        <Flex gap="small">
          <Button
            className={styles.button}
            onClick={() => {
              goGitHub("https://github.com/agentscope-ai/agentscope");
            }}
          >
            <AgentscopeLogoIcon style={{ marginLeft: -5 }} />
            AgentScope GitHub
            <SparkUpperrightArrowLine style={{ fontSize: "20px" }} />
          </Button>
          <Button
            className={styles.button}
            onClick={() => {
              goGitHub(
                "https://github.com/agentscope-ai/agentscope-samples/tree/main/alias",
              );
            }}
          >
            <AlisaLogoIcon style={{ marginLeft: -5 }} />
            Alias GitHub
            <SparkUpperrightArrowLine style={{ fontSize: "20px" }} />
          </Button>
        </Flex>
      </div>
      <Welcome
        style={{ justifyContent: "center", flex: 1 }}
        logo={null}
        title={
          <div className={styles.title}>
            <div className={styles.logo}>
              <LogoIcon className="w-full h-full object-cover" />
            </div>
            <div className={styles.label}>
              : Start It Now, Extend It Your Way, Deploy All with Ease
            </div>
          </div>
        }
        desc={
          <div className={styles.description}>
            Let the Agent help you with everything you want to do
          </div>
        }
      />
    </Flex>
  );
};

export default memo(WelcomeView);
