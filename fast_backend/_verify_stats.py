"""一次性验证脚本：Pydantic v2 Decimal 序列化 + 统计 SQL 编译 + app 导入"""
from decimal import Decimal

# 1) Pydantic v2 Decimal -> JSON 是什么形态？
from pydantic import BaseModel


class M(BaseModel):
    x: Decimal


print("pydantic json-mode Decimal:", M(x=Decimal("8000.00")).model_dump(mode="json"))

# 2) FastAPI jsonable_encoder 对 Pydantic 模型（by_alias 默认值）
from fastapi.encoders import jsonable_encoder

print("jsonable_encoder:", jsonable_encoder({"d": M(x=Decimal("8000.00"))}))

# 3) 统计 SQL 能否正常编译（验证 case/coalesce/select_from 用法）
from sqlalchemy import case, func, select
from sqlalchemy.dialects import mysql

from models.category import Category
from models.record import Record

stmt = (
    select(
        func.coalesce(func.sum(case((Category.type == 1, Record.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Category.type == 0, Record.amount), else_=0)), 0),
    )
    .select_from(Record)
    .outerjoin(Category, Record.category_id == Category.id)
    .where(
        Record.user_id == 1,
        Record.status == 1,
        Record.date >= "2026-05-01",
        Record.date < "2026-06-01",
    )
)
print(stmt.compile(dialect=mysql.dialect()))

# 4) 整个 app 能否导入（覆盖 crud/statistics.py 之前的语法错误）
import main  # noqa: F401

print("main import OK")

# 5) MonthlyStatisticsOut 按别名输出
from schemas.statistics import MonthlyStatisticsOut

out = MonthlyStatisticsOut(
    year=2026, month=5, total_income=Decimal("8000.00"), total_expense=Decimal("3500.00")
)
print("MonthlyStatisticsOut json:", jsonable_encoder(out))
