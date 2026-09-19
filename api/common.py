from typing import Any, Callable, Optional

from services.errors import ServiceError


def header_default(header_factory: Optional[Callable[..., Any]], alias: str) -> Any:
    if header_factory is None:
        return None
    return header_factory(default=None, alias=alias)


def raise_http_error(service_error: ServiceError, http_exception_cls: Optional[type[Exception]]) -> None:
    if http_exception_cls is None:
        raise service_error
    raise http_exception_cls(status_code=service_error.status_code, detail=service_error.detail) from service_error
