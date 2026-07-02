"""Configuration models for finders."""
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional, Self


class AgentConfig(BaseModel):
    """Agent 运行时配置。"""

    model: str = Field(default="deepseek-v4-flash", description="LLM 模型名称")
    fast_model: str = Field(default="deepseek-v4-flash", description="快速模型（用于压缩等辅助任务）")
    max_iterations: int = Field(default=10, ge=1, le=50)
    recursion_limit: int = Field(default=100, ge=1, le=1000, description="Agent 递归调用限制")
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
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_model: Optional[str] = None

    # Search
    tavily_api_key: Optional[str] = None
    exasearch_api_key: Optional[str] = None

    # Financial Data
    financial_datasets_api_key: Optional[str] = None

    # Workspace
    finders_workspace: Optional[str] = None
    # Project directory (Finders 项目代码根路径)
    finders_project_dir: Optional[str] = None

    # Sub-configs
    agent: AgentConfig = Field(default_factory=AgentConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)

    @model_validator(mode="after")
    def _apply_llm_config(self) -> Self:
        """Apply LLM_MODEL env var to override default model name."""
        if self.llm_model:
            if self.agent.model == "deepseek-v4-flash":
                self.agent.model = self.llm_model
            if self.agent.fast_model == "deepseek-v4-flash":
                self.agent.fast_model = self.llm_model
        return self

    def get_workspace_path(self) -> Path:
        """Get the sandbox workspace path.

        Uses FINDERS_WORKSPACE env var if set, otherwise defaults to
        ~/.finders/workspace.
        """
        if self.finders_workspace:
            return Path(self.finders_workspace).expanduser().resolve()
        return Path.home() / ".finders" / "workspace"

    def get_project_dir(self) -> Path:
        """Get the Finders project root directory.

        Uses FINDERS_PROJECT_DIR env var if set, otherwise defaults to
        ~/.finders/project.
        """
        if self.finders_project_dir:
            return Path(self.finders_project_dir).expanduser().resolve()
        return Path.home() / ".finders" / "project"

    def create_chat_model(self, model_name: str | None = None, fast: bool = False):
        """Create a ChatOpenAI model instance using LLM_API_KEY and LLM_API_BASE.

        Args:
            model_name: Override model name. If None, uses agent.model (or agent.fast_model if fast=True).
            fast: If True and model_name is None, use agent.fast_model.
        """
        from langchain_openai import ChatOpenAI

        model = model_name or (self.agent.fast_model if fast else self.agent.model)
        return ChatOpenAI(
            model=model,
            api_key=self.llm_api_key,
            base_url=self.llm_api_base,
        )


def get_settings() -> Settings:
    """获取全局设置（单例）。"""
    if not hasattr(get_settings, "_instance"):
        get_settings._instance = Settings()
    return get_settings._instance
