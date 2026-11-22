from fastapi import HTTPException, Request


def get_current_user_id(request: Request) -> str:
    """Read identity set by the platform authentication middleware.

    The RAG API deliberately does not accept user_id from a header, form or model output.
    """
    user_id = getattr(request.state, "user_id", None)
    if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 128:
        raise HTTPException(status_code=401, detail="请先登录")
    return user_id
