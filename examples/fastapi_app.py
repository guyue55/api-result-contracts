"""无身份或存储的最小适配示例，不是生产业务服务器。"""

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from api_result_contracts import ContractError, make_registry
from api_result_contracts.integrations.fastapi import ContractRouter, install_fastapi


class Item(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    quantity: int


registry = make_registry("example")
app = FastAPI()
api = ContractRouter(registry=registry, prefix="/api/v2")


@api.post("/echo", data_model=Item)
async def echo(value: Item):
    return value


@api.get("/conflict", data_model=Item, errors=[409001])
async def conflict():
    raise ContractError(409001)


app.include_router(api)
install_fastapi(app, registry=registry, api_prefixes=("/api/v2",))
