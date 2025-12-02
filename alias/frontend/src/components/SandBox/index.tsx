import React, { useEffect, memo } from "react";
import { Result } from "@agentscope-ai/design";
import styles from "./index.module.scss";

interface SandBoxProps {
  sandboxUrl: string;
}

const SandBox: React.FC<SandBoxProps> = ({ sandboxUrl }) => {
  return (
    <div className={styles.sandbox}>
      {/* <div className={styles.title}>{sandboxUrl}</div> */}
      {sandboxUrl && (
        <iframe
          src={sandboxUrl}
          className={styles.sandboxIframe}
          title="Sandbox"
          allowFullScreen
          frameBorder="0"
        />
      )}
      {!sandboxUrl && (
        <Result
          type="error"
          title="Error"
          description="Please try again later"
        />
      )}
    </div>
  );
};

export default memo(SandBox);
