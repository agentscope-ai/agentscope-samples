import React from "react";
import { RouterProvider } from "react-router-dom";
import {
  ConfigProvider,
  carbonTheme,
  carbonDarkTheme,
} from "@agentscope-ai/design";
import { router } from "./routes";
import { WorkspaceProvider } from "@/context/WorkspaceContext.tsx";
import { ThemeProvider, useTheme } from "@/context/ThemeContext.tsx";
import { MessageProvider } from "@/context/MessageContext";

const AppContent: React.FC = () => {
  const { theme: currentTheme } = useTheme();
  const theme = currentTheme === "dark" ? carbonDarkTheme : carbonTheme;
  const prefix = "sps";
  return (
    <ConfigProvider
      {...theme}
      prefix={prefix}
      prefixCls={prefix}
      iconfont="//at.alicdn.com/t/a/font_4807885_ugexdeaoq7.js"
      style={{
        width: "100%",
        height: "100%",
      }}
    >
      <WorkspaceProvider>
        <MessageProvider>
          <RouterProvider router={router} />
        </MessageProvider>
      </WorkspaceProvider>
    </ConfigProvider>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
