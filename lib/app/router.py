from fastapi import APIRouter


class Router(APIRouter):


    def __init__(self, *, prefix = "", tags = None, dependencies = None,responses = None, callbacks = None, routes = None, redirect_slashes = True, default = None, dependency_overrides_provider = None, on_startup = None, on_shutdown = None, lifespan = None, deprecated = None, include_in_schema = True):
        super().__init__(prefix=prefix, tags=tags, dependencies=dependencies,responses=responses, callbacks=callbacks, routes=routes, redirect_slashes=redirect_slashes, default=default, dependency_overrides_provider=dependency_overrides_provider, on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan, deprecated=deprecated, include_in_schema=include_in_schema)


    