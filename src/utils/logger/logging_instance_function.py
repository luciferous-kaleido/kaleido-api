from datetime import datetime
from functools import wraps
from typing import Callable
from uuid import uuid7
from zoneinfo import ZoneInfo

from .logger import Logger

jst = ZoneInfo("Asia/Tokyo")


def logging_instance_function(
    logger: Logger,
    endpoint_attr_name: str,
    *,
    write: bool = False,
    with_return: bool = True,
    with_args: bool = True,
) -> Callable:
    def decorator_logging_class_function(func: Callable) -> Callable:
        @wraps(func)
        def wrapper_logging_class_function(self, *args, **kwargs):
            obj_type = type(self)
            class_name = obj_type.__name__
            endpoint_name = getattr(self, endpoint_attr_name)
            function_name = func.__name__
            call_id = str(uuid7())
            dt_start = datetime.now(tz=jst)
            try:
                data_start = {"FunctionName": function_name, "CallID": call_id}
                if with_args:
                    data_start["Args"] = args
                    data_start["KwArgs"] = kwargs
                if write:
                    logger.debug(
                        f"start function `{class_name}.{function_name}` ({call_id})",
                        endpoint=endpoint_name,
                        data=data_start,
                    )

                result = func(self, *args, **kwargs)

                delta = datetime.now(tz=jst) - dt_start
                data_end = {
                    "FunctionName": function_name,
                    "CallID": call_id,
                    "Duration": {
                        "str": str(delta),
                        "TotalSeconds": delta.total_seconds(),
                    },
                }
                if with_args:
                    data_end["Args"] = args
                    data_end["KwArgs"] = kwargs
                if with_return:
                    data_end["Return"] = result
                if write:
                    logger.debug(
                        f"succeeded function `{class_name}.{function_name} ({call_id})`",
                        endpoint=endpoint_name,
                        data=data_end,
                    )

                return result
            except Exception as e:
                delta = datetime.now(tz=jst) - dt_start

                logger.debug(
                    f"failed function `{class_name}.{function_name}`",
                    endpoint=endpoint_name,
                    exc_info=True,
                    data={
                        "FunctionName": function_name,
                        "CallID": call_id,
                        "Duration": {
                            "str": str(delta),
                            "TotalSeconds": delta.total_seconds(),
                        },
                        "Args": args,
                        "KwArgs": kwargs,
                        "Error": {"type": str(type(e)), "message": str(e)},
                    },
                )

                raise

        return wrapper_logging_class_function

    return decorator_logging_class_function
