import { Button, Modal } from "@agentscope-ai/design";
import { memo, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./index.module.scss";

const LoginModal = () => {
  const [isModalOpen, setIsModalOpen] = useState<boolean>(true);
  const navigate = useNavigate();
  const showModal = () => {
    setIsModalOpen(true);
  };

  const handleOk = () => {
    setIsModalOpen(false);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
  };
  if (
    localStorage.getItem("access_token") === null &&
    localStorage.getItem("refresh_token") === null
  )
    return (
      <Modal
        // title="Basic Modal"
        open={isModalOpen}
        onOk={handleOk}
        onCancel={handleCancel}
        footer={null}
        centered={true}
        width={384}
        closable={false}
      >
        <div className={styles.modalWrap}>
          <h1>Welcome</h1>
          <p className={styles.tips}>
            Login or register to chat with AgentScope, upload files and images,
            generate images or videos, etc.
          </p>
          <Button
            type="primary"
            className={styles.logBtn}
            onClick={() => {
              navigate("/login?mode=login");
            }}
          >
            Login
          </Button>
          <Button
            className={styles.registerBtn}
            onClick={() => {
              navigate("/login?mode=register");
            }}
          >
            Register
          </Button>
        </div>
      </Modal>
    );
  return null;
};
export default memo(LoginModal);
