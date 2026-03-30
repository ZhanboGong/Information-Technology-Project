# apps/core/utils/error_messages.py

AI_ERRORS = {
    "API_CONNECTION_FAILED": "",
    "INVALID_JSON_RESPONSE": "。",
    "FILE_READ_ERROR": "",
    "MODEL_LIMIT_REACHED": "",
    "UNKNOWN_ERROR": ""
}

def get_ai_error(code, detail=""):
    """

    :param code:
    :param detail:
    :return:
    """
    msg = AI_ERRORS.get(code, AI_ERRORS["UNKNOWN_ERROR"])
    if detail:
        return f"{msg} | Detail: {detail}"
    return msg