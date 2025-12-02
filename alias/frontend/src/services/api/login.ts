import { Register } from "@/types/api";
import { request } from "./request";
import { RegisterParams, LoginParams } from "../types/login";
export const loginApi = {
  // Register
  register: (params: RegisterParams) => {
    return request.post<Register>("/api/v1/register", {
      ...params,
    });
  },
  login: (params: LoginParams) => {
    return request.post<Register>("/api/v1/login", {
      ...params,
    });
  },
  getUsers: () => {
    return request.get<Register>("/api/v1/users/me");
  },
};
