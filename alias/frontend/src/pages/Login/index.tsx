import { loginApi } from "@/services/api/login";
import { message } from "@agentscope-ai/design";
import {
  SparkEmailLine,
  SparkLockLine,
  SparkUserLine,
} from "@agentscope-ai/icons";
import type { ProFormInstance } from "@ant-design/pro-components";
import {
  LoginForm,
  ProConfigProvider,
  ProFormText,
} from "@ant-design/pro-components";
import { theme } from "antd";
import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./index.module.scss";

export const Login = () => {
  const { token } = theme.useToken();
  const formRef = useRef<ProFormInstance>();
  const urlParams = new URLSearchParams(window.location.search);
  const mode = urlParams.get("mode");
  const navigate = useNavigate();
  const onFinish = async () => {
    try {
      const values = await formRef?.current?.validateFields();
      if (mode === "register") {
        delete values?.repassword;
        const register = await loginApi.register(values);
        message.success("Registration successful");
        navigate("/login?mode=login");
        const { payload } = register;
        if (payload?.access_token)
          localStorage.setItem("access_token", payload?.access_token);
        if (payload?.refresh_token)
          localStorage.setItem("refresh_token", payload?.refresh_token);
        // console.log(register, "register");
      }
      if (mode === "login") {
        const login = await loginApi.login(values);
        const { payload } = login;
        if (payload?.access_token)
          localStorage.setItem("access_token", payload?.access_token);
        if (payload?.refresh_token)
          localStorage.setItem("refresh_token", payload?.refresh_token);
        navigate("/");
      }
    } catch (errorInfo: any) {
      if (mode === "login") {
        message.error(errorInfo?.response?.data?.detail || "Login failed");
      }
      if (mode === "register") {
        message.error(
          errorInfo?.response?.data?.detail || "Registration failed",
        );
      }
    }
  };
  return (
    <div className={styles.container}>
      <div className={styles.logWrap}>
        <ProConfigProvider hashed={false}>
          <div style={{ backgroundColor: token.colorBgContainer }}>
            <LoginForm title="AgentScope" formRef={formRef} onFinish={onFinish}>
              {mode === "register" && (
                <ProFormText
                  name="username"
                  fieldProps={{
                    size: "large",
                    prefix: <SparkUserLine className={"prefixIcon"} />,
                  }}
                  placeholder={"Please enter your username"}
                  rules={[
                    {
                      required: true,
                      message: "Please enter your username!",
                    },
                  ]}
                />
              )}

              <ProFormText
                name="email"
                fieldProps={{
                  size: "large",
                  prefix: <SparkEmailLine className={"prefixIcon"} />,
                }}
                placeholder={"Please enter your email"}
                rules={[
                  {
                    required: true,
                    message: "Please enter your email!",
                  },
                  {
                    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: "Please enter a valid email address",
                  },
                ]}
              />
              <ProFormText.Password
                name="password"
                fieldProps={{
                  size: "large",
                  prefix: <SparkLockLine className={"prefixIcon"} />,
                }}
                placeholder={"Please enter your password"}
                rules={[
                  {
                    required: true,
                    message: "Please enter your password",
                  },
                  {
                    pattern: /^\S{2,40}$/,
                    message: "Please enter a valid password",
                  },
                ]}
              />
              {mode === "register" && (
                <ProFormText.Password
                  name="repassword"
                  fieldProps={{
                    size: "large",
                    prefix: <SparkLockLine className={"prefixIcon"} />,
                  }}
                  placeholder={"Please enter your password again"}
                  rules={[
                    {
                      required: true,
                      message: "Please enter your password",
                    },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue("password") === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(
                          new Error("Passwords do not match, please re-enter"),
                        );
                      },
                    }),
                  ]}
                />
              )}
            </LoginForm>
          </div>
        </ProConfigProvider>
      </div>
    </div>
  );
};
export default Login;
