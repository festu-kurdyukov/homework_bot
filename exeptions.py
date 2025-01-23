class ResponseStatusCodeNot200(Exception):
    """Ответ сервера не равен 200."""


class APIRequestException(Exception):
    """Сбой при запросе к эндпоинту."""


class ParseStatusError(Exception):
    """Нестандартный статус в ответе."""