"""Configuration models for finders."""
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional


class AgentConfig(BaseModel):
    """Agent 运行时配置。"""

    model: str = Field(default="openai:gpt-5", description="LLM 模型")
    fast_model: str = Field(default="openai:gpt-5-mini", description="快速模型（用于压缩等辅助任务）")
    max_iterations: int = Field(default=10, ge=1, le=50)
    compact_threshold: int = Field(default=100_000, description="触发压缩的 token 阈值")
    enable_todo: bool = Field(default=True, description="启用 TODO 任务清单（分解复杂任务）")


class MemoryConfig(BaseModel):
    """Memory 系统配置。"""

    enabled: bool = True
    chunk_tokens: int = Field(default=400, ge=100)
    chunk_overlap: int = Field(default=80, ge=0)
    max_results: int = Field(default=6, ge=1)
    min_score: float = Field(default=0.1, ge=0, le=1)
    half_life_days: float = Field(default=30, gt=0)
    mmr_lambda: float = Field(default=0.7, ge=0, le=1)


class ToolConfig(BaseModel):
    """工具配置。"""

    web_search_provider: str = Field(default="tavily", description="tavily | exa")
    max_concurrency: int = Field(default=10, ge=1)
    max_calls_per_tool: int = Field(default=3, ge=1)


class Settings(BaseSettings):
    """全局设置（从环境变量 + YAML 加载）。"""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # LLM
    openai_api_key: Optional[str] = None

    # Search
    tavily_api_key: Optional[str] = None
    exasearch_api_key: Optional[str] = None

    # Financial Data
    financial_datasets_api_key: Optional[str] = None

    # Sub-configs
    agent: AgentConfig = Field(default_factory=AgentConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)


def get_settings() -> Settings:
    """获取全局设置（单例）。"""
    if not hasattr(get_settings, "_instance"):
        get_settings._instance = Settings()
    return get_settings._instance
