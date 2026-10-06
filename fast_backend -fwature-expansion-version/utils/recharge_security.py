"""支付回调签名 — HMAC-SHA256（模拟网关与未来真实渠道适配器共用）

安全定位：支付回调是充值链路**唯一**能把订单推进到「已支付/待审批」的闸口
（用户端不存在任何完成订单的端点）。签名保证该闸口只接受持有服务端密钥的
网关事件——密钥不出服务端，客户端无法伪造"支付成功"。

- 签名覆盖 order_no | amount | status 三个字段；金额与订单应收的核对在
  crud.apply_payment_callback 里再做一次（签名防伪造，金额核对防网关侧改单）。
- 比较用 hmac.compare_digest（常数时间），防时序侧信道逐字节猜签名。
- 回调重放无害：状态机 + 行锁保证同一订单只入账一次（见 crud 层说明），
  因此不需要额外的时间戳/nonce 机制。
"""

import hashlib
import hmac
from dataclasses import dataclass

from config.settings import RECHARGE_CALLBACK_SECRET

# 网关侧支付结果白名单：构造事件时校验，状态机只认这两个值
PAYMENT_STATUSES = ("success", "fail")


def callback_sign(order_no: str, amount: str, status: str) -> str:
    """按网关事件三字段计算 HMAC-SHA256 签名（模拟网关侧的行为）"""
    message = f"{order_no}|{amount}|{status}"
    return hmac.new(
        RECHARGE_CALLBACK_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_callback_sign(order_no: str, amount: str, status: str, sign: str) -> bool:
    """校验回调签名；任何缺参/类型异常一律视为无效"""
    if not sign or not isinstance(sign, str):
        return False
    try:
        expected = callback_sign(order_no, amount, status)
    except Exception:
        return False
    return hmac.compare_digest(expected, sign)


@dataclass(frozen=True)
class PaymentEvent:
    """已验签的网关支付事件 — 订单状态机推进的唯一合法输入

    只能通过 build_payment_event() 构造（签名校验在其内部），绕过验签拿不到实例；
    crud.apply_payment_callback 只接受本类型，从类型层面封死"未验签直接入账"的路径。
    """

    order_no: str
    amount: str   # 网关上报金额原串（签名覆盖的就是它；与订单应收的 Decimal 核对在 crud 层）
    status: str   # success=支付成功 fail=支付失败/用户取消


def build_payment_event(order_no: str, amount: str, status: str, sign: str) -> PaymentEvent | None:
    """验签并构造网关事件；签名无效/参数非法返回 None（调用方转 401）

    服务端模拟网关也走这里：先 callback_sign() 生成签名再 build——生成与校验
    代码路径和真实渠道适配器完全一致。
    """
    if not order_no or not amount or status not in PAYMENT_STATUSES:
        return None
    if not verify_callback_sign(order_no, amount, status, sign):
        return None
    return PaymentEvent(order_no=order_no, amount=amount, status=status)
