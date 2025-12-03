import { request } from "./request";

export const HabbitApi = {
  getUserProfiling: (uid: string): Promise<any> => {
    return request.post(
      "/alias_memory_service/user_profiling/show_all_user_profiles",
      { uid },
    );
  },
  updateProfiling: (
    uid: string,
    pid: string,
    content_before: string,
    content_after: string,
  ): Promise<any> => {
    return request.post(
      "/alias_memory_service/user_profiling/direct_update_profile",
      { uid, pid, content_before, content_after },
    );
  },
  addProfiling: (uid: string, content: string): Promise<any> => {
    return request.post(
      "/alias_memory_service/user_profiling/direct_add_profile",
      { uid, content },
    );
  },
  deleteProfiling: (uid: string, pid: string): Promise<any> => {
    return request.post(
      "/alias_memory_service/user_profiling/direct_delete_by_profiling_id",
      { uid, pid },
    );
  },
  confirmProfiling: (uid: string, pid: string): Promise<any> => {
    return request.post(
      "/alias_memory_service/user_profiling/direct_confirm_profile",
      { uid, pid },
    );
  },
};
