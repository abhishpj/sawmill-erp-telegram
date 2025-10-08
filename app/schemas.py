from pydantic import BaseModel, Field
from typing import Optional

class StockIn(BaseModel):
    type: str = "STOCK_IN"
    supplier_name: str
    qty_logs: int = Field(gt=0)
    volume_cft: Optional[float] = Field(default=None, ge=0)
    date_str: Optional[str] = None

class Production(BaseModel):
    type: str = "PRODUCTION"
    batch_id: int
    thickness_mm: float = Field(gt=0)
    width_mm: float = Field(gt=0)
    length_mm: Optional[float] = Field(default=None, gt=0)
    qty: int = Field(gt=0)
    date_str: Optional[str] = None

class Order(BaseModel):
    type: str = "ORDER"
    customer_name: str
    qty: int = Field(gt=0)
    size_label: Optional[str] = None
    thickness_mm: Optional[float] = Field(default=None, gt=0)
    width_mm: Optional[float] = Field(default=None, gt=0)
    length_mm: Optional[float] = Field(default=None, gt=0)
    date_str: Optional[str] = None

class Delivery(BaseModel):
    type: str = "DELIVERY"
    order_id: int
    lorry_number: str
    date_str: Optional[str] = None

class Payment(BaseModel):
    type: str = "PAYMENT"
    order_id: int
    amount: float = Field(gt=0)
    method: Optional[str] = None
    date_str: Optional[str] = None

class ReportReq(BaseModel):
    type: str = "REPORT"
    kind: str = "daily"
