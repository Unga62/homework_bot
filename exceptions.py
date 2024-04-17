class ApiError(Exception):
    """Обработка исключений для запроса к эндпоинту."""


class EmptyApiResponse(ApiError):
    """Обработка исключений пустого ответа от API."""


class TokenError(Exception):
    """Обработка исключений ошибки в токенах."""
