"""公共 Pydantic 模型 — ORM 派生基类"""

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    """ORM 模型基类 — 自动启用 from_attributes + populate_by_name

    参考项目每个 schema 重复写 ConfigDict(from_attributes=True, populate_by_name=True)；
    这里集中到 OrmBase，*Out 类继承即可。
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
