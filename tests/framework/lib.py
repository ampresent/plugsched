# Copyright 2019-2022 Alibaba Group Holding Limited.
# SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause

import time
from typing import Callable, Any

def retry(
    work: Callable,
    retries: int,
    expected: str,
    *args,
    finish='',
    **kwargs
) -> Any:

    while retries > 0:
        try:
            return work(*args, **kwargs)
        except Exception as e:
            str_e = str(e)
            if expected in str_e:
                retries -= 1
                time.sleep(5)
            elif finish and finish in str_e:
                return None
            else:
                raise
    raise Exception("Reached maximum retrying.")
