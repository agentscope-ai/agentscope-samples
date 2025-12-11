import type { GetProps } from "antd";
import Icon from "@ant-design/icons";

type CustomIconComponentProps = GetProps<typeof Icon>;
const AgentscopeLogoIconSvg = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    version="1.1"
    width="20"
    height="20"
    viewBox="0 0 20 20"
  >
    <defs>
      <clipPath id="master_svg0_75_00637">
        <rect x="0" y="0" width="20" height="20" rx="10" />
      </clipPath>
      <pattern
        x="2"
        y="2"
        width="16"
        height="16"
        patternUnits="userSpaceOnUse"
        id="master_svg1_75_01073"
      >
        <image
          x="0"
          y="0"
          width="16"
          height="16"
          href="data:image/png;base64,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"
        />
      </pattern>
    </defs>
    <g clip-path="url(#master_svg0_75_00637)">
      <rect
        x="0"
        y="0"
        width="20"
        height="20"
        rx="10"
        fill="currentColor"
        fillOpacity="1"
      />
      <g>
        <rect
          x="2"
          y="2"
          width="16"
          height="16"
          rx="0"
          fill="url(#master_svg1_75_01073)"
          fillOpacity="1"
        />
      </g>
    </g>
  </svg>
);
const AgentscopeLogoIcon = (props: Partial<CustomIconComponentProps>) => (
  <Icon component={AgentscopeLogoIconSvg} {...props} />
);

export default AgentscopeLogoIcon;
