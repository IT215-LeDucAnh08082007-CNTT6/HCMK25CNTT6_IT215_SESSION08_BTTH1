from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

app = FastAPI()

class BaseResponse(BaseModel):
    statusCode: int
    message: str
    data: Optional[Any] = None
    error: Optional[Any] = None
    timestamp: str
    path: str

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse(
            statusCode=exc.status_code,
            message="Thất bại",
            error=exc.detail,
            timestamp=datetime.now(timezone.utc).isoformat(),
            path=request.url.path
        ).model_dump()
    )

def success_response(status_code: int, message: str, data: Any, path: str):
    return JSONResponse(
        status_code=status_code,
        content=BaseResponse(
            statusCode=status_code,
            message=message,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            path=path
        ).model_dump()
    )

carriers = [
    {"id": 1, "code": "GHN", "name": "Giao Hang Nhanh", "max_weight_capacity": 5000, "status": "ACTIVE"},
    {"id": 2, "code": "GHTK", "name": "Giao Hang Tiet Kiem", "max_weight_capacity": 3000, "status": "ACTIVE"},
    {"id": 3, "code": "VTP", "name": "Viettel Post", "max_weight_capacity": 10000, "status": "SUSPENDED"}
]

shipments = [
    {"id": 1, "carrier_id": 1, "order_reference": "ORD-2026-001", "total_weight": 4200, "dispatch_date": "2026-07-01", "shift": "MORNING"}
]

class CarrierSchema(BaseModel):
    code: str
    name: str = Field(..., min_length=3)
    max_weight_capacity: int = Field(..., gt=0)
    status: str

class ShipmentSchema(BaseModel):
    carrier_id: int
    order_reference: str
    total_weight: int = Field(..., gt=0)
    dispatch_date: str
    shift: str

@app.get("/carriers")
def get_carriers(req: Request, keyword: Optional[str] = None, status: Optional[str] = None, min_weight: Optional[int] = None):
    result = carriers
    if keyword:
        result = [c for c in result if keyword.lower() in c["code"].lower() or keyword.lower() in c["name"].lower()]
    if status:
        result = [c for c in result if c["status"] == status]
    if min_weight is not None:
        result = [c for c in result if c["max_weight_capacity"] >= min_weight]
    return success_response(200, "Danh sách đối tác", result, req.url.path)

@app.get("/carriers/{carrier_id}")
def get_carrier(carrier_id: int, req: Request):
    carrier = next((c for c in carriers if c["id"] == carrier_id), None)
    if not carrier:
        raise HTTPException(404, "Carrier not found")
    return success_response(200, "Chi tiết đối tác", carrier, req.url.path)

@app.post("/carriers")
def create_carrier(carrier: CarrierSchema, req: Request):
    if carrier.status not in ["ACTIVE", "INACTIVE", "SUSPENDED"]:
        raise HTTPException(400, "Trạng thái không hợp lệ")
    if any(c["code"] == carrier.code for c in carriers):
        raise HTTPException(400, "Mã đối tác đã tồn tại")
    new_carrier = {"id": max([c["id"] for c in carriers], default=0) + 1, **carrier.model_dump()}
    carriers.append(new_carrier)
    return success_response(201, "Tạo đối tác thành công", new_carrier, req.url.path)

@app.put("/carriers/{carrier_id}")
def update_carrier(carrier_id: int, carrier: CarrierSchema, req: Request):
    for c in carriers:
        if c["id"] == carrier_id:
            c.update(carrier.model_dump())
            return success_response(200, "Cập nhật đối tác thành công", c, req.url.path)
    raise HTTPException(404, "Carrier not found")

@app.delete("/carriers/{carrier_id}")
def delete_carrier(carrier_id: int, req: Request):
    for i, c in enumerate(carriers):
        if c["id"] == carrier_id:
            carriers.pop(i)
            return JSONResponse(status_code=204, content=None)
    raise HTTPException(404, "Carrier not found")

@app.post("/shipments")
def create_shipment(s: ShipmentSchema, req: Request):
    if s.shift not in ["MORNING", "AFTERNOON", "NIGHT"]:
        raise HTTPException(400, "Ca làm việc không hợp lệ")
    carrier = next((c for c in carriers if c["id"] == s.carrier_id), None)
    if not carrier:
        raise HTTPException(404, "Carrier not found")
    if carrier["status"] != "ACTIVE":
        raise HTTPException(400, "Đối tác không đang hoạt động")
    if s.total_weight > carrier["max_weight_capacity"]:
        raise HTTPException(400, "Vượt quá tải trọng tối đa")
    if any(sh["carrier_id"] == s.carrier_id and sh["dispatch_date"] == s.dispatch_date and sh["shift"] == s.shift for sh in shipments):
        raise HTTPException(400, "Trùng lịch điều phối")
    new_shipment = {"id": len(shipments) + 1, **s.model_dump()}
    shipments.append(new_shipment)
    return success_response(201, "Khởi tạo chuyến hàng thành công", new_shipment, req.url.path)

@app.get("/shipments")
def get_shipments(req: Request):
    return success_response(200, "Danh sách chuyến hàng", shipments, req.url.path)