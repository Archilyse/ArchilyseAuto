from functools import wraps
from typing import Type, Union

from marshmallow import Schema


def celery_schema(
    args: Union[Type[Schema], Schema, None] = None,
    kwargs: Union[Type[Schema], Schema, None] = None,
    dump: Union[Type[Schema], Schema, None] = None,
):
    """Decorator that applies a Marshmallow schema to the input and/or output of a Celery task.

    Args:
        args (marshmallow.Schema or type[marshmallow.Schema] or None):
            Marshmallow schema used to deserialize the input arguments of the Celery task.
            Only the first arg is deserialized as this is the argument/ result passed on from the parent task(s).
            If a type is passed, it will be instantiated with no arguments. Defaults to None.
        kwargs (marshmallow.Schema or type[marshmallow.Schema] or None):
            Marshmallow schema used to deserialize the keyword arguments of the Celery task.
            If a type is passed, it will be instantiated with no arguments. Defaults to None.
        dump (marshmallow.Schema or type[marshmallow.Schema] or None):
            Marshmallow schema used to serialize the output of the Celery task.
            If a type is passed, it will be instantiated with no arguments. Defaults to None.

    Returns:
        callable:
            The decorated function.

    Examples:
        Define a schema for the input arguments and output of a Celery task:

        >>> from marshmallow import Schema, fields
        >>> class AddSchema(Schema):
        ...     a = fields.Integer(required=True)
        ...     b = fields.Integer(required=True)
        >>> class ResultSchema(Schema):
        ...     result = fields.Integer()

        Use the schema to deserialize the input arguments and serialize the output of a Celery task:

        >>> @celery_app.task()
        ... @celery_schema(args=AddSchema(), dump=ResultSchema())
        ... def add(a, b):
        ...     return {"result": sum(a, b)}

        >>> add.delay({"a": 1, "b": 2}).get()
        {'result': 3}

        Use the schema to deserialize the keyword arguments of a Celery task:

        >>> @celery_app.task()
        ... @celery_schema(kwargs=AddSchema(), dump=ResultSchema())
        ... def add(a, b):
        ...     return {"result": sum([a, b])}

        >>> add.delay(a=1, b=2).get()
        {'result': 3}

        Apply the deserialized arguments as keyword arguments to the wrapped function:

        >>> @celery_app.task()
        ... @celery_schema(args=AddSchema())
        ... def add(a_and_b):
        ...     return sum(a_and_b.values())

        >>> add.delay({"a": 1, "b": 2}).get()
        3
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if args is not None:
                args_schema = args() if isinstance(args, type) else args
                a = (args_schema.load(a[0]), *a[1:])

            if kwargs is not None:
                kwargs_schema = kwargs() if isinstance(kwargs, type) else kwargs
                kw.update(kwargs_schema.load(kw))

            if dump is not None:
                schema = dump() if isinstance(dump, type) else dump
                return schema.dump(f(*a, **kw))
            return f(*a, **kw)

        return wrapper

    return decorator
