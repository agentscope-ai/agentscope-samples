import { HabbitApi } from "@/services/api/habbit";
import {
  AlertDialog,
  Button,
  Dropdown,
  IconButton,
  Input,
  message,
  Modal,
  Tooltip,
} from "@agentscope-ai/design";
import {
  SparkCopyLine,
  SparkDeleteLine,
  SparkDownArrowLine,
  SparkEditLine,
  SparkMoreLine,
  SparkPlusLine,
  SparkSearchLine,
  SparkUserCheckedLine,
} from "@agentscope-ai/icons";
import { Flex, List } from "antd";
import copy from "copy-to-clipboard";
import React, { memo, useEffect, useMemo, useState } from "react";
import styles from "./index.module.scss";

interface MetadataProps {
  session_id: string;
  is_confirmed: number;
}
interface HabbitDataProps {
  content: string;
  pid: string;
  uid: string;
  metadata: MetadataProps;
}

interface HabbitModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  uid: string;
}
const { TextArea } = Input;

const Header: React.FC<{
  searchKeyword: string;
  setSearchKeyword: (value: string) => void;
  copyHandle: () => void;
  downHandle: () => void;
  addHabbit: () => void;
}> = ({
  searchKeyword,
  setSearchKeyword,
  copyHandle,
  downHandle,
  addHabbit,
}) => {
  const fontSize = { fontSize: "20px" };

  return (
    <Flex gap="large" justify="space-between" style={{ padding: "20px 0" }}>
      <Flex style={{ width: "200px" }}>
        <Input
          placeholder="Search Knowledge..."
          prefix={<SparkSearchLine style={fontSize} />}
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
        />
      </Flex>
      <Flex gap="small">
        <Button type="text" onClick={copyHandle}>
          <SparkCopyLine style={fontSize} />
        </Button>
        <Dropdown
          menu={{
            items: [
              {
                key: "1",
                label: "Download",
                icon: <SparkDownArrowLine style={{ fontSize: 20 }} />,
                onClick: downHandle,
              },
              {
                key: "2",
                label: "Delete",
                danger: true,
                icon: <SparkDeleteLine style={{ fontSize: 20 }} />,
                onClick: () => {
                  AlertDialog.warning({
                    title: "Confirm deletion of all habbits?",
                    children:
                      "Once deleted, it cannot be recovered. Please proceed with caution.",
                    centered: true,
                    okText: "Confirm deletion",
                    onOk: () => {},
                  });
                },
              },
            ],
          }}
        >
          <Button type="text">
            <SparkMoreLine style={fontSize} />
          </Button>
        </Dropdown>
        <Button type="primary" onClick={addHabbit}>
          <SparkPlusLine style={fontSize} /> Add Habbit
        </Button>
      </Flex>
    </Flex>
  );
};

const HabbitModal: React.FC<HabbitModalProps> = (props) => {
  const { open, setOpen, uid } = props;
  const [editOpen, setEditOpen] = useState(false);
  const [habbitContent, setHabbitContent] = useState("");
  const [contentBefore, setContentBefore] = useState("");
  const [pid, setPid] = useState("");
  const [loading, setLoading] = useState(false);
  const [dataList, setDataList] = useState<HabbitDataProps[]>([]);
  const [searchKeyword, setSearchKeyword] = useState("");

  const getProfilingData = () => {
    HabbitApi.getUserProfiling(uid)
      .then((res: { data: HabbitDataProps[] }) => {
        const data = res?.data;
        if (data && Array.isArray(data)) setDataList(data);
      })
      .catch((e) => {
        message.error("Network error");
      });
  };

  useEffect(() => {
    if (open) getProfilingData();
  }, [open]);

  // Use useMemo to implement filtering logic
  const filteredDataList = useMemo(() => {
    if (!searchKeyword) return dataList;

    return dataList.filter((item) =>
      item.content.toLowerCase().includes(searchKeyword.toLowerCase()),
    );
  }, [dataList, searchKeyword]);

  const addHabbit = () => {
    setEditOpen(true);
    setHabbitContent("");
    setPid("");
  };

  const editHabbit = (contents: string) => {
    setEditOpen(true);
    setHabbitContent(contents);
    setContentBefore(contents);
  };

  const copyHandle = () => {
    if (dataList.length > 0) {
      const contents = JSON.stringify(dataList, null, 2);
      if (contents) {
        copy(contents);
        message.success("Copied successfully");
      }
    }
  };

  const downHandle = () => {
    if (dataList.length > 0) {
      try {
        const contents = JSON.stringify(dataList, null, 2);
        const blob = new Blob([contents], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "habbits.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (error) {
        message.error("Download failed");
      }
    }
  };

  const onClose = () => {
    setOpen(false);
    setSearchKeyword("");
  };
  const getTitle = () => {
    if (pid) return "Edit habbit";
    return "Add habbit";
  };

  const onCloseEdit = () => {
    setEditOpen(false);
  };
  const deleteProfiling = async (uid: string, pid: string) => {
    try {
      const result = await HabbitApi.deleteProfiling(uid, pid);
      if (result) {
        getProfilingData();
        message.success("successfully deleted habbit!");
      }
    } catch (error) {
      message.error("Failed to delete habbit");
    }
  };
  const onSure = async () => {
    if (!habbitContent) {
      message.info("Please enter habbit");
      return;
    }
    try {
      setLoading(true);
      if (pid) {
        // edit habbit
        if (contentBefore.trim() === habbitContent.trim()) {
          onCloseEdit();
          confirmProfiling(uid, pid);
          return;
        }
        const result = await HabbitApi.updateProfiling(
          uid,
          pid,
          contentBefore,
          habbitContent,
        );
        if (result) {
          getProfilingData();
          message.success("Habbit edited successfully!");
        }
      } else {
        // add habbit
        const result = await HabbitApi.addProfiling(uid, habbitContent);
        if (result) {
          getProfilingData();
          message.success("Habbit added successfully!");
        }
      }
    } catch (error) {
      message.error("Network error");
    } finally {
      setLoading(false);
      onCloseEdit();
    }
  };
  const confirmProfiling = (uid: string, pid: string) => {
    try {
      HabbitApi.confirmProfiling(uid, pid).then((res) => {
        if (res) getProfilingData();
      });
    } catch (error) {
      console.error("Error confirming profiling:", error);
      message.error("Failed to confirm habit");
    }
  };
  return (
    <>
      <Modal
        title="Preserved Habbit"
        open={open}
        width={800}
        footer={false}
        onCancel={onClose}
        maskClosable={false}
      >
        <div style={{ height: "50vh", overflow: "auto" }}>
          <div>
            Habbit enables Alias to learn user's preference and task specific
            best practices.
          </div>
          {/* Use extracted Header component */}
          <Header
            searchKeyword={searchKeyword}
            setSearchKeyword={setSearchKeyword}
            copyHandle={copyHandle}
            downHandle={downHandle}
            addHabbit={addHabbit}
          />
          <List
            dataSource={filteredDataList}
            renderItem={(item) => (
              <List.Item className={styles.listItem}>
                <div className={styles.textEllipsis}>{item.content}</div>
                <div className={styles.icon}>
                  <Flex align="center" gap="small">
                    <Dropdown
                      menu={{
                        items: [
                          {
                            key: "1",
                            label: "Edit",
                            icon: <SparkEditLine style={{ fontSize: 20 }} />,
                            onClick: () => {
                              editHabbit(item.content);
                              setPid(item.pid);
                            },
                          },
                          {
                            key: "2",
                            label: "Delete",
                            danger: true,
                            icon: <SparkDeleteLine style={{ fontSize: 20 }} />,
                            onClick: () => {
                              AlertDialog.warning({
                                title: "Confirm deletion of this habbits?",
                                children:
                                  "Once deleted, it cannot be recovered. Please proceed with caution.",
                                centered: true,
                                okText: "Confirm deletion",
                                onOk: () => {
                                  deleteProfiling(item.uid, item.pid);
                                },
                              });
                            },
                          },
                        ],
                      }}
                    >
                      <IconButton
                        size="middle"
                        shape="default"
                        className={styles.actionButtons}
                        icon={<SparkMoreLine style={{ fontSize: 20 }} />}
                      />
                    </Dropdown>
                    {item.metadata.is_confirmed === 0 && (
                      <Tooltip title="You need to manually click to confirm for it to take effect">
                        <IconButton
                          size="middle"
                          shape="default"
                          icon={
                            <SparkUserCheckedLine style={{ fontSize: 20 }} />
                          }
                          onDoubleClick={() => {
                            confirmProfiling(item.uid, item.pid);
                          }}
                        />
                      </Tooltip>
                    )}
                  </Flex>
                </div>
              </List.Item>
            )}
          />
        </div>
      </Modal>
      <Modal
        title={getTitle()}
        open={editOpen}
        width={700}
        okText="Sure"
        onCancel={onCloseEdit}
        maskClosable={false}
        onOk={onSure}
        footer={
          <Flex gap={16} align="center" justify="flex-end">
            <Button onClick={onCloseEdit}>Cancel</Button>
            <Button type="primary" loading={loading} onClick={onSure}>
              Sure
            </Button>
          </Flex>
        }
      >
        <TextArea
          rows={Math.min(Math.max(3, habbitContent.split("\n").length + 1), 20)}
          onChange={(v) => {
            setHabbitContent(v.target.value || "");
          }}
          value={habbitContent}
          autoSize={{ minRows: 3, maxRows: 20 }}
        />
      </Modal>
    </>
  );
};

export default memo(HabbitModal);
