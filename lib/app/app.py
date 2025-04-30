from fastapi import FastAPI, Request
from .globals import APP
from starlette.middleware.base import BaseHTTPMiddleware
import time

class ASGILatencyWrapper:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        print(scope,receive)
        print("ssl ",scope.get('ssl_cert', None) )
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()

        async def send_wrapper(message):
            # Only capture when response is sent (could be 'http.response.start' or 'http.response.body')
            if message["type"] == "http.response.start":
                end_time = time.perf_counter()
                latency = end_time - start_time
                message['headers'].append((b'X-Request-Latency',f'{latency:.3f} s'.encode()))
                message['headers'].append((b'Server',f'SMO'.encode()))
                message['headers'].append((b'Via',f'SMO/1.1'.encode()))

                print(f"🔁 [Application-level latency]: {latency:.6f} seconds")
            await send(message)

        await self.app(scope, receive, send_wrapper)


class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Record the start time
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate latency
        latency = time.time() - start_time

        # Add the latency to the response headers
        #response.headers["X-Request-Latency"] = str(latency)

        return response

class App(FastAPI):

    def __init__(self, *, debug = False, routes = None, title = "Infy APP", summary = None, description = "", version = "0.1.0", openapi_url = "/openapi.json", openapi_tags = None, servers = None, dependencies = None,redirect_slashes = True, docs_url = "/docs", redoc_url = "/redoc", swagger_ui_oauth2_redirect_url = "/docs/oauth2-redirect", swagger_ui_init_oauth = None, middleware = None, exception_handlers = None, on_startup = None, on_shutdown = None, lifespan = None, terms_of_service = None, contact = None, license_info = None, openapi_prefix = "", root_path = "", root_path_in_servers = True, responses = None, callbacks = None, webhooks = None, deprecated = None, include_in_schema = True, swagger_ui_parameters = None, separate_input_output_schemas = True, **extra):
        super().__init__(debug=debug, routes=routes, title=title, summary=summary, description=description, version=version, openapi_url=openapi_url, openapi_tags=openapi_tags, servers=servers, dependencies=dependencies, redirect_slashes=redirect_slashes, docs_url=docs_url, redoc_url=redoc_url, swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url, swagger_ui_init_oauth=swagger_ui_init_oauth, middleware=middleware, exception_handlers=exception_handlers, on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan, terms_of_service=terms_of_service, contact=contact, license_info=license_info, openapi_prefix=openapi_prefix, root_path=root_path, root_path_in_servers=root_path_in_servers, responses=responses, callbacks=callbacks, webhooks=webhooks, deprecated=deprecated, include_in_schema=include_in_schema, swagger_ui_parameters=swagger_ui_parameters, separate_input_output_schemas=separate_input_output_schemas, **extra)
        self.add_middleware(LatencyMiddleware)
        APP['Main'] = self

    def __call__(self, scope, receive, send,*args, **kwargs):
        return super().__call__(scope, receive, send)

    #@classmethod
    def run(self,host:str,port:str,*args,ssl:bool=False,certfile:str='',keyfile:str='',sslport:int=0,reload:bool=False,debug:bool=False,autossl:bool=False,h3:bool=False, sslpem:bool=False,**kwargs):
        from hypercorn import Config
        config = Config()
        config.bind = [f'{host}:{port}']
        config.insecure_bind = [f'{host}:{port}']
        config.include_server_header = False
        #config.worker_class = 'asyncio'
        config.debug = debug or False
        if ssl:
            if sslport:
                config.bind = [f'{host}:{sslport}']
                if h3:
                    config.quic_bind = [f'{host}:{sslport}']
            else:
                if h3:
                    config.quic_bind = [f'{host}:{port}']
            config.ssl_handshake_timeout = 10
            if sslpem is not None and (certfile and keyfile):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as cfile , tempfile.NamedTemporaryFile(delete=False) as kfile:
                    cfile.write(certfile.encode()) , kfile.write(keyfile.encode())
                    cfile.flush() , kfile.flush()
                    certfile , keyfile = cfile.name , kfile.name
                config.certfile = certfile
                config.keyfile = keyfile
                pass
            elif certfile and keyfile:
                config.certfile = certfile
                config.keyfile = keyfile
            else:
                raise Exception('SSL/TLS Cert Files Missing')

        from hypercorn.asyncio import serve
        from asyncio import run

        run(serve(ASGILatencyWrapper(self),config=config,mode='asgi'),debug=debug)

    def start(self,host:str,port:str,ssl:bool=False,certfile:str='',keyfile:str='',sslport:int=0,reload:bool=False,debug:bool=False,autossl:bool=False,h3:bool=False, sslpem:bool=False,workers=1):
        from .runner import startMP
        startMP(host,port,ssl=ssl,certfile=certfile,keyfile=keyfile,sslport=sslport,reload=reload,debug=debug,autossl=autossl,h3=h3,sslpem=sslpem,workers=workers)
