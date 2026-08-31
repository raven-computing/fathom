# Copyright (C) 2026 Raven Computing
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Provides the `@noexcept` function decorator."""

import sys
import functools

from typing import Any, Callable, Optional, TypeVar, NoReturn
from typing import cast, overload


F = TypeVar("F", bound=Callable[..., Any])

NoexceptHandler = Callable[[Callable[..., Any], Exception], NoReturn]


def _system_noexcept_handler(func: Callable, ex: Exception) -> NoReturn:
    print(
        f"Error: Function {func.__name__}() raised an unexpected exception "
        f"of type {type(ex).__name__}:\n"
        f"{ex}\n\n"
        "This is likely a programming error. "
        "Please report this defect to the software vendor.\n"
        "Fatal: noexcept violation. Terminating program.",
        file=sys.stderr,
    )
    raise SystemExit(126) # Code usually used for UNKNOWN_ERROR


@overload
def noexcept(func: F) -> F:
    ...
@overload
def noexcept(*, handler: NoexceptHandler) -> Callable[[F], F]:
    ...
def noexcept(
    func: Optional[F] = None,
    *,
    handler: NoexceptHandler = _system_noexcept_handler
):
    """Decorator that ensures a function does not raise any exceptions.

    Usage of the `@noexcept` decorator is recommended when application code
    must ensure that a given function returns normally/unexceptionably.
    This decorator not only servers as a documentation marker for affected
    source code, but also enforces this requirement by catching any unhandled
    exception raised by the decorated function. Conceptually, applying this
    decorator to a function means that the application code has no sensible way
    of handling exceptions that may originate from that function, and thus
    prefers instead to terminate immediately.

    The provided system handler, which is used by default, terminates the
    program in case of an unexpected exception. Additionally, the decorator
    allows for a custom exception handler to be provided. If the decorated
    function raises an exception, the provided handler will be invoked with
    the function object and the exception as arguments (in that order).
    Please note that the handler is expected to terminate the program, as the
    decorated function is not allowed to raise any exceptions, and cannot
    return normally in case of an exception. Failing to terminate will result
    in undefined behaviour.

    The following is an example of using a custom handler:

    ```
    def my_custom_handler(func: Callable, ex: Exception) -> NoReturn:
        print("This is not okay")
        sys.exit(1)

    @noexcept(handler=my_custom_handler)
    def my_func():
        do_something_that_may_raise()

    ```

    Do not use `@noexcept` as a substitute for proper exception handling.
    """

    def _decorate(target: F) -> F:
        @functools.wraps(target)
        def wrapper(*args, **kwargs):
            try:
                return target(*args, **kwargs)
            except Exception as ex:  # pylint: disable=broad-exception-caught
                handler(target, ex)

        return cast(F, wrapper)

    return _decorate if func is None else _decorate(func)
