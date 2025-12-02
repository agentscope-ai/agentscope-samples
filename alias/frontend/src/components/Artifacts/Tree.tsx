import type { NodeRendererProps } from "react-arborist";
import { Tree } from "react-arborist";
import {
  BsFile,
  BsFiles,
  BsFiletypeCss,
  BsFiletypeHtml,
  BsFiletypeJava,
  BsFiletypeJs,
  BsFiletypeJsx,
  BsFiletypeMd,
  BsFiletypePy,
  BsFiletypeTsx,
  BsFolder2Open,
  BsImage,
} from "react-icons/bs";
import { FaFileExcel, FaFilePowerpoint, FaFileWord } from "react-icons/fa";
import { FiArchive, FiFilm, FiFolder } from "react-icons/fi";
import "./Tree.scss";
// Node data type
interface FileNode {
  name: string;
  type: "directory" | "file";
  path: string;
  children?: FileNode[];
}

interface FileTreeProps {
  data: FileNode[];
  onExpand: (node: FileNode) => void;
  show: string;
}

// Add sorting function
const sortFileTree = (nodes: FileNode[]): FileNode[] => {
  return nodes
    .sort((a, b) => {
      // First sort by type (directories first)
      if (a.type !== b.type) {
        return a.type === "directory" ? -1 : 1;
      }
      // Then sort by name alphabetically
      return a.name.localeCompare(b.name);
    })
    .map((node) => ({
      ...node,
      children: node.children ? sortFileTree(node.children) : undefined,
    }));
};

function getFileType(name: string, isFolder: boolean, isOpen: boolean) {
  const ext = name.split(".").pop()?.toLowerCase();
  const iconStyle = { color: "#6b7280" };
  if (isFolder) {
    return isOpen ? (
      <BsFolder2Open className="icon" />
    ) : (
      <FiFolder className="icon" />
    );
  }
  if (!ext) {
    return <BsFile style={iconStyle} className="icon" />;
  }
  switch (ext) {
    case "js":
      return <BsFiletypeJs style={{ color: "#f1e05a" }} className="icon" />;
    case "py":
      return <BsFiletypePy style={iconStyle} className="icon" />;
    case "md":
      return <BsFiletypeMd style={iconStyle} className="icon" />;
    case "tsx":
      return <BsFiletypeTsx style={iconStyle} className="icon" />;
    case "jsx":
      return <BsFiletypeJsx style={{ color: "#f1e05a" }} className="icon" />;
    case "java":
      return <BsFiletypeJava style={iconStyle} className="icon" />;
    case "json":
      return <BsFiles style={{ color: "#f5de19" }} className="icon" />;
    case "css":
      return <BsFiletypeCss style={iconStyle} className="icon" />;
    case "html":
      return <BsFiletypeHtml style={iconStyle} className="icon" />;
    case "png":
    case "jpg":
    case "jpeg":
      return <BsImage style={iconStyle} className="icon" />;
    case "docx":
    case "doc":
      return <FaFileWord style={{ color: "#2b579a" }} className="icon" />;
    case "zip":
    case "tar.gz":
    case "rar":
      return <FiArchive style={iconStyle} className="icon" />;
    case "xlsx":
    case "xls":
      return <FaFileExcel style={{ color: "#217346" }} className="icon" />;
    case "pptx":
    case "ppt":
      return <FaFilePowerpoint style={{ color: "#d24726" }} className="icon" />;
    case "mp4":
    case "mov":
    case "avi":
      return <FiFilm style={iconStyle} className="icon" />;
    default:
      return <BsFile style={iconStyle} className="icon" />;
  }
}

export const FileTree = ({ data, onExpand, show }: FileTreeProps) => {
  // Sort data
  const sortedData = sortFileTree(data);

  // Custom node renderer
  const CustomNode = ({
    node,
    style,
    dragHandle,
  }: NodeRendererProps<FileNode>) => {
    const isFolder = node.data.type === "directory";
    const icon = getFileType(node.data.name, isFolder, node.isOpen);
    // Correct method to get node level
    const getNodeLevel = () => {
      let level = 0;
      let parent = node.parent;
      while (parent) {
        level++;
        parent = parent.parent;
      }
      return level - 1;
    };

    return (
      <div
        ref={dragHandle}
        //   className={`node ${node.state.isSelected ? 'selected' : ''}` }
        className={`node
          ${node.state.isSelected ? "selected" : ""}
          level-${getNodeLevel()}
        `}
        onClick={() => {
          node.isInternal && node.toggle();
          if (show === "noShow") {
            onExpand(node?.data);
          }
        }}
        aria-expanded={node.isOpen}
      >
        <div className="node-content">
          {icon}
          <span className="node-text">{node.data.name}</span>
          {/* {node.isInternal && (
              <span className="arrow">{node.isOpen ? '▼' : '▶'}</span>
            )} */}
        </div>
      </div>
    );
  };
  return (
    <Tree<FileNode>
      data={sortedData}
      idAccessor={(node) => node.path}
      openByDefault={false}
      indent={20}
      width={"100%"}
    >
      {CustomNode}
    </Tree>
  );
};
