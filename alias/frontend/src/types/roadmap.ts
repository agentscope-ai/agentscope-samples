export enum RoadMapType {
  TODO = "todo",
  IN_PROGRESS = "in_progress",
  DONE = "done",
  ABANDONED = "abandoned",
}
export interface UpdateItem {
  reason_for_status: string;
  task_done: string;
  progress_summary: string;
  next_step: string;
  tool_usage_summary: string;
  worker: string;
  attempt_idx: number;
}

export interface Worker {
  worker_index: string;
  worker_name: string;
  status: string;
}

export interface SubtaskSpecification {
  subtask_description: string;
  input_intro: string;
  exact_input: string;
  expected_output: string;
  desired_auxiliary_tools: string;
}
export interface RoadMapTask {
  subtask_specification: SubtaskSpecification;
  status: "Done" | "Planned" | "In-process";
  updates: UpdateItem[];
  attempt: number;
  workers: Worker[];
  explanation?: string;
}

export interface RoadMap {
  original_task: string;
  decomposed_tasks: RoadMapTask[];
}

type ChangeKind = "E" | "N" | "D" | "A";

interface ChangeItem {
  kind: ChangeKind;
  lhs?: any;
  rhs?: any;
}

export interface Change {
  path: string[];
  kind: ChangeKind;
  lhs?: any;
  rhs?: any;
  index?: number;
  item?: ChangeItem;
}
export interface SubtasksProps {
  description: string;
  state: RoadMapType;
  key?: number;
}
export interface RoadMapDataProps {
  subtasks: SubtasksProps[];
}

export interface RoadMapMessage {
  previous: RoadMapDataProps | null;
  current: RoadMapDataProps;
}
