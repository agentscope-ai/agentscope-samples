"""DeepFinance Reader

从 JSON 文件加载任务数据，并现场组装 init_messages。
- 数据来源：训练集/测试集 JSON 文件
- 消息组装：加载 prompt 模板 + query
- 工具调用：仍走 env_service
"""
import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

from ajet.schema.task import Task
from ajet.task_reader.task_reader_base import BaseTaskReader

# 配置 logger
logger = logging.getLogger(__name__)

# 控制 debug 输出的开关（可通过环境变量控制）
DEBUG_ENABLED = os.environ.get("DEEPFINANCE_DEBUG", "0") == "1"

def _debug_log(msg: str):
    """统一的 debug 日志输出"""
    if DEBUG_ENABLED:
        print(f"[DEBUG][DeepFinanceReader] {msg}")
    logger.debug(msg)


class DeepFinanceReader(BaseTaskReader):
    """
    DeepFinance 专用的数据加载器
    
    特点：
    1. 从 JSON 文件加载任务数据（支持 list 和 dict 格式）
    2. 现场组装 init_messages（system_prompt + user_query）
    3. env_type 固定为 "deep_finance"，由 env_service 负责工具调用
    """
    
    # 类级别缓存
    _prompt_template_cache = None
    _tool_prompt_cache = None
    
    def __init__(self, reader_config):
        super().__init__(reader_config)
        self.reader_config = reader_config
        
        _debug_log(f"Initializing DeepFinanceReader...")
        _debug_log(f"reader_config type: {type(reader_config).__name__}")
        
        # 获取 prompt 目录路径
        self.local_path = os.path.dirname(os.path.abspath(__file__))
        _debug_log(f"local_path: {self.local_path}")
        
        # 初始化 prompt 缓存
        self._init_prompt_templates()
        _debug_log(f"Initialization complete.")
    
    def _init_prompt_templates(self):
        """初始化 prompt 模板缓存"""
        if DeepFinanceReader._prompt_template_cache is None:
            prompt_file = os.path.join(self.local_path, 'prompt', 'finance_analyst_prompt.md')
            _debug_log(f"Loading prompt template from: {prompt_file}")
            with open(prompt_file, 'r', encoding='utf-8') as f:
                DeepFinanceReader._prompt_template_cache = f.read()
            _debug_log(f"Prompt template loaded, length: {len(DeepFinanceReader._prompt_template_cache)} chars")
        else:
            _debug_log(f"Using cached prompt template, length: {len(DeepFinanceReader._prompt_template_cache)} chars")
        
        if DeepFinanceReader._tool_prompt_cache is None:
            # 使用 tool_prompt_builder.py 中的静态模板
            _debug_log(f"Loading tool prompt template...")
            from tutorial.example_deep_finance.prompt.tool_prompt_builder import get_tool_prompt_template
            DeepFinanceReader._tool_prompt_cache = get_tool_prompt_template()
            _debug_log(f"Tool prompt template loaded, length: {len(DeepFinanceReader._tool_prompt_cache)} chars")
        else:
            _debug_log(f"Using cached tool prompt template, length: {len(DeepFinanceReader._tool_prompt_cache)} chars")
    
    def _build_system_prompt(self) -> str:
        """构建 system prompt"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        _debug_log(f"Building system prompt with date: {current_date}")
        
        # 替换日期占位符
        system_prompt = DeepFinanceReader._prompt_template_cache.replace(
            '{current_date}', 
            current_date
        )
        # 替换工具列表占位符
        system_prompt = system_prompt.replace(
            '{tool_list}', 
            DeepFinanceReader._tool_prompt_cache
        )
        _debug_log(f"System prompt built, final length: {len(system_prompt)} chars")
        return system_prompt
    
    def _build_init_messages(self, query: str) -> List[Dict[str, Any]]:
        """
        构建 init_messages
        
        Args:
            query: 用户问题
            
        Returns:
            [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        _debug_log(f"Building init_messages for query (len={len(query)}): {query[:100]}..." if len(query) > 100 else f"Building init_messages for query: {query}")
        system_prompt = self._build_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        _debug_log(f"init_messages built: {len(messages)} messages, system_prompt_len={len(system_prompt)}")
        return messages
    
    def _read_json_file(self, file_path: str, split: str = "train") -> List[Task]:
        """
        从 JSON 文件读取任务列表
        
        支持的数据格式：
        1. List 格式: [{"task": {"task_id": ..., "query": ...}, ...}, ...]
        2. Dict 格式: {"task_id_1": {"task": {...}, ...}, "task_id_2": {...}, ...}
        
        Args:
            file_path: JSON 文件路径
            split: 数据集划分（train/val）
            
        Returns:
            List[Task]: 任务列表
        """
        _debug_log(f"Reading JSON file: {file_path}, split={split}")
        
        if not os.path.exists(file_path):
            _debug_log(f"ERROR: File not found: {file_path}")
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        _debug_log(f"JSON data loaded, type: {type(data).__name__}, size: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
        
        tasks = []
        skipped_count = 0
        split_filtered_count = 0
        
        # 解析数据
        if isinstance(data, list):
            # List 格式
            _debug_log(f"Parsing List format data, total items: {len(data)}")
            for idx, item in enumerate(data):
                task_info = item.get('task', {})
                task_id = task_info.get('task_id', '')
                query = task_info.get('query', '')
                
                if not task_id or not query:
                    skipped_count += 1
                    _debug_log(f"  Item {idx}: SKIPPED (missing task_id or query)")
                    continue
                
                # 过滤 split
                item_split = task_info.get('metadata', {}).get('split', split)
                if item_split != split:
                    split_filtered_count += 1
                    _debug_log(f"  Item {idx} ({task_id}): FILTERED by split (item_split={item_split}, expected={split})")
                    continue
                
                # 构建 Task
                _debug_log(f"  Item {idx} ({task_id}): Creating task...")
                task = self._create_task(task_id, query, item)
                tasks.append(task)
                
        elif isinstance(data, dict):
            # Dict 格式
            _debug_log(f"Parsing Dict format data, total keys: {len(data)}")
            for idx, (task_id, item) in enumerate(data.items()):
                task_info = item.get('task', {})
                query = task_info.get('query', '')
                
                if not query:
                    skipped_count += 1
                    _debug_log(f"  Key {idx} ({task_id}): SKIPPED (missing query)")
                    continue
                
                # 过滤 split
                item_split = task_info.get('metadata', {}).get('split', split)
                if item_split != split:
                    split_filtered_count += 1
                    _debug_log(f"  Key {idx} ({task_id}): FILTERED by split (item_split={item_split}, expected={split})")
                    continue
                
                # 构建 Task（使用 dict key 作为 task_id）
                _debug_log(f"  Key {idx} ({task_id}): Creating task...")
                task = self._create_task(task_id, query, item)
                tasks.append(task)
        
        _debug_log(f"Summary: loaded={len(tasks)}, skipped={skipped_count}, split_filtered={split_filtered_count}")
        print(f"[DeepFinanceReader] Loaded {len(tasks)} tasks from {file_path} (split={split})")
        
        if len(tasks) == 0:
            raise ValueError(f"No tasks found in file: {file_path} for split={split}")
        
        return tasks
    
    def _create_task(self, task_id: str, query: str, raw_item: Dict[str, Any]) -> Task:
        """
        创建 Task 对象
        
        Args:
            task_id: 任务 ID
            query: 用户问题
            raw_item: 原始数据项
            
        Returns:
            Task: 任务对象
        """
        _debug_log(f"Creating Task: task_id={task_id}")
        
        # 现场组装 init_messages
        init_messages = self._build_init_messages(query)
        
        # 提取 metadata
        task_info = raw_item.get('task', {})
        metadata = task_info.get('metadata', {})
        
        # 将原始数据存入 metadata，供 env 和 judge 使用
        # 注意：序列化为 JSON 字符串，避免嵌套字典导致 PyArrow 序列化时递归深度超限
        metadata['raw_task_data'] = json.dumps(raw_item, ensure_ascii=False)
        metadata['query'] = query
        metadata['confidence'] = raw_item.get('confidence', 1.0)
        metadata['rubrics'] = raw_item.get('rubrics', None)
        metadata['ground_truth'] = task_info.get('ground_truth', '')
        
        _debug_log(f"  Task metadata: confidence={metadata['confidence']}, has_rubrics={metadata['rubrics'] is not None}, has_ground_truth={bool(metadata['ground_truth'])}")
        _debug_log(f"  Task init_messages: {len(init_messages)} messages")
        
        task = Task(
            main_query=query,
            init_messages=init_messages,
            task_id=task_id,
            env_type="deep_finance",  # 固定为 deep_finance，由 env_service 处理
            metadata=metadata
        )
        _debug_log(f"  Task created successfully: {task_id}")
        return task
    
    def get_training_tasks(self) -> List[Task]:
        """获取训练任务"""
        _debug_log(f"get_training_tasks() called")
        file_path = self.reader_config.deep_finance.training.file_path
        _debug_log(f"Training file path: {file_path}")
        tasks = self._read_json_file(file_path, split="train")
        _debug_log(f"get_training_tasks() returning {len(tasks)} tasks")
        return tasks
    
    def get_validation_tasks(self) -> List[Task]:
        """获取验证任务"""
        _debug_log(f"get_validation_tasks() called")
        file_path = self.reader_config.deep_finance.validation.file_path
        _debug_log(f"Validation file path: {file_path}")
        tasks = self._read_json_file(file_path, split="val")
        _debug_log(f"get_validation_tasks() returning {len(tasks)} tasks")
        return tasks
