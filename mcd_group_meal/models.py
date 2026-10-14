"""企业团餐业务数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Store:
    store_code: str
    be_code: str
    store_name: str
    reservation: bool
    reservation_time_options: list[dict] = field(default_factory=list)
    business_status: bool = True
    business_start_time: str = ""
    business_end_time: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Store":
        return cls(
            store_code=d.get("storeCode", ""),
            be_code=d.get("beCode", ""),
            store_name=d.get("storeName", ""),
            reservation=bool(d.get("reservation")),
            reservation_time_options=d.get("reservationTimeOptions", []) or [],
            business_status=bool(d.get("businessStatus", True)),
            business_start_time=d.get("businessStartTime", ""),
            business_end_time=d.get("businessEndTime", ""),
        )

    @property
    def short_name(self) -> str:
        return self.store_name.replace("麦当劳", "").replace("餐厅", "")


@dataclass
class MealAssistance:
    """助餐服务项（GMS001/002/003）。"""

    gm_service_code: str
    gm_service_name: str
    service_items: list[str]
    selected: bool = False
    enable: bool = True
    unusable_reason: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "MealAssistance":
        return cls(
            gm_service_code=d.get("gmServiceCode", ""),
            gm_service_name=d.get("gmServiceName", ""),
            service_items=d.get("serviceItems", []) or [],
            selected=bool(d.get("selected")),
            enable=bool(d.get("enable", True)),
            unusable_reason=d.get("unusableReason", ""),
        )

    @property
    def needs_advance_booking(self) -> bool:
        """专人分餐/摆台（GMS002/003）需提前预约。"""
        return self.gm_service_code in ("GMS002", "GMS003")

    @property
    def available_now(self) -> bool:
        return self.enable


@dataclass
class Promotion:
    """满折/满减规则（beTypes=6 团餐专属）。"""

    promotion_id: str
    gm_service_code: str
    discount: int
    start_discount_point: int  # 起扣点（分，100分=1元）
    products: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Promotion":
        rule = (d.get("ruleDetail") or {}).get("orderDiscount") or {}
        return cls(
            promotion_id=str(d.get("promotionId", "")),
            gm_service_code=d.get("gmServiceCode", ""),
            discount=int(rule.get("discount", 0)),
            start_discount_point=int(rule.get("startDiscountPoint", 0)),
            products=[p.get("productCode", "") for p in d.get("products", [])],
        )

    @property
    def threshold_yuan(self) -> float:
        return self.start_discount_point / 100.0


@dataclass
class PriceItem:
    product_code: str
    quantity: int

    def to_dict(self) -> dict:
        return {"productCode": self.product_code, "quantity": self.quantity}


@dataclass
class PriceResult:
    """calculate-price 归一化结果。"""

    raw: dict
    subtotal: float = 0.0
    payable: float = 0.0
    discount_rate: Optional[float] = None  # 当前折率，如 0.74 表示 74 折
    balance_points: int = 0  # 距下一档还差多少分
    next_rate: Optional[float] = None
    errors: list[str] = field(default_factory=list)

    @property
    def balance_yuan(self) -> float:
        return self.balance_points / 100.0


@dataclass
class GroupPlanLine:
    product_code: str
    name: str
    quantity: int
    unit_price: float


@dataclass
class GroupPlan:
    headcount: int
    per_person_budget: float
    lines: list[GroupPlanLine]
    total_quantity: int = 0
    subtotal: float = 0.0
    notes: list[str] = field(default_factory=list)
