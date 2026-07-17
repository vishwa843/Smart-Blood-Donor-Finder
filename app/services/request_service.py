"""Blood request service helpers."""


def create_request_summary(request_id: int):
    return {"request_id": request_id, "status": "pending"}
