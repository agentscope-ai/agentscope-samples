import UserHeader from "@/assets/icons/avatar/avatar.svg";
import { Popover } from "@agentscope-ai/design";
import { SparkEscapeLine, SparkSwitchLine } from "@agentscope-ai/icons";
import { Flex } from "antd";
import React, { memo } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./index.module.scss";

interface UserInfoProps {
  uid: string;
  userName: string;
  email: string;
}
interface AvatarProps {
  userInfo: UserInfoProps;
}
const Avatar: React.FC<AvatarProps> = ({ userInfo }) => {
  const navigate = useNavigate();
  const logOutHandle = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login?mode=login");
  };
  return (
    <Popover
      placement="rightTop"
      trigger="click"
      overlayClassName={styles.userPopover}
      content={
        <div className={styles.popoverAvatarContent}>
          <Flex className={styles.userInfo}>
            <div className={styles.header}>
              <img
                src={UserHeader}
                alt="User"
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <div className={styles.name}>{userInfo?.userName || ""}</div>
              <div className={styles.email}>{userInfo?.email || ""}</div>
            </div>
          </Flex>
          <Flex vertical className={styles.userButton}>
            <Flex
              gap="small"
              align="center"
              className={styles.item}
              onClick={logOutHandle}
            >
              <SparkSwitchLine style={{ fontSize: 18 }} />
              Switch account
            </Flex>
            <Flex
              gap="small"
              align="center"
              className={styles.item}
              onClick={logOutHandle}
            >
              <SparkEscapeLine style={{ fontSize: 18 }} /> Log out
            </Flex>
          </Flex>
        </div>
      }
    >
      <button className={styles.headerButton}>
        <div className="w-8 h-8 rounded-full bg-gray-200 overflow-hidden">
          <img
            src={UserHeader}
            alt="User"
            className="w-full h-full object-cover"
          />
        </div>
      </button>
    </Popover>
  );
};

export default memo(Avatar);
