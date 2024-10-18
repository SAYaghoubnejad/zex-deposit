from sanic import Sanic, Blueprint, Request, json
from sanic.response.types import JSONResponse

from .db.models import TransferStatus, ChainId
from .db.transfer import find_transactions_by_status

app = Sanic(name="ZexDeposit")

bp = Blueprint(name="transfer", url_prefix="/transfers", version=1)

app.blueprint(bp)


@bp.get("/finalized/<chain_id:int>")
async def get_finalized_tx(request: Request, chain_id: int) -> JSONResponse:
    from_block = int(request.args.get("from_block", 0))
    transfers = await find_transactions_by_status(
        TransferStatus.FINALIZED, chain_id=ChainId(chain_id), from_block=from_block
    )
    return json(body=[transfer.model_dump() for transfer in transfers])
