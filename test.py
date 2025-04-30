from lib import CertManger
from fastapi import Request, Response, WebSocket
from fastapi.routing import APIRoute
from json import dumps
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from requests import request
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Route(BaseModel):
    name: str
    description: str | None = None
    path: str
    backend: str | None = None
    methods:list[str] = ['GET']

class DelRoute(BaseModel):
    path:str
    methods:list[str] = ['GET']


cm = CertManger()

p , c, _ = cm.gen_CA('VRAG','Basic RunTime API Gateway', alt_names=['*.abc.com',"127.0.0.1"])
print("CA\n",c)
pp, cc, __ = cm.gen_cert(c,p,'localhost','VRAG',alt_names=['infy','localhost','127.0.0.1','0.0.0.0'])
print("Cert\n",cc)
from lib import App

app = App(debug=True,title='VRAG API',summary='Basic RunTime API Gateway',version='1.0.0')


@app.get('/hello',tags=["APIM"],operation_id='get_hello',name='hello',response_class=JSONResponse, status_code=200)
def hello():
    return {'message': 'hello world'}

@app.get('/welcome',tags=["APIM"],name='Welcome API')
def welcome():
    return {'message' : 'Its welcome api'}

@app.post('/add',tags=["APIM"],name='Add new Route')
def add(route:Route):
    i = len(app.router.routes)
    async def runner():
        resp = request('GET',route.backend,verify=False)
        #data = resp.json() or resp.text
        return Response(resp.text, resp.status_code,resp.headers,resp.headers['content-type'])
    app.add_api_route(route.path,runner,methods=route.methods,name=route.name,tags=[route.name])
    print(i, len(app.router.routes))
    app.router.routes = [r for r in app.router.routes if r.include_in_schema]
    app.openapi_schema = None
    app.setup()
    return {'message':f'{route.path} added'}


@app.post('/delete',tags=["APIM"],name='Delete Route')
def delete(delroute:DelRoute):
    i = len(app.router.routes)
    app.router.routes = [r for r in app.router.routes if not ( isinstance(r, APIRoute) and r.path == delroute.path and set(r.methods) == set(delroute.methods))]
    print(i, len(app.router.routes))
    if i > len(app.router.routes):
        app.router.routes = [r for r in app.router.routes if r.include_in_schema]
        app.openapi_schema = None
        app.setup()
        return {'message':f'{delroute.path} Removed'}
    else:
        app.router.routes = [r for r in app.router.routes if r.include_in_schema]
        app.openapi_schema = None
        app.setup()
        return JSONResponse({'message': f'{delroute.path} unable to remove'},500)
    

@app.get('/routes',tags=['APIM'],name='Get All Routes',)
async def allroutes():
    return [ {"path": r.path , "methods": r.methods ,"name": r.name, "schema": r.include_in_schema} for r in app.router.routes]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, request:Request=None):
        if request is not None:
            print(request.url)
            print("Headers\n",request.headers)
            print("Scope\n",request.scope)
            print("cookies\n",request.cookies)
            print("Client\n",request.client)

        print(websocket.url)
        print("state\n",websocket.state)
        print("Scope\n",websocket.scope)
        print("Headers\n",websocket.headers)
        print("Client\n",websocket.client)
        print("cookies\n",websocket.cookies)
        print("client state\n",websocket.client_state)
        #print("Session\n",websocket.session)
        #print("User\n",websocket.user)
        #print("App\n",websocket.app)
        await websocket.accept(headers=[(b'Server',b'SMO')])
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
            await websocket.close()
            break

import websocket
import rel
websocket.enableTrace(True)

@app.get('/run_ws',tags=['APIM'],name='run ws')
def run_ws():
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as cfile , tempfile.NamedTemporaryFile(delete=False) as kfile, tempfile.NamedTemporaryFile(delete=False) as cafile:
        cfile.write(cc.encode()) , kfile.write(pp.encode()), cafile.write(c.encode())
        cfile.flush() , kfile.flush(), cafile.flush()
    ws = websocket.create_connection("wss://localhost:8443/ws",header=["Test: Working"],sslopt={
        "certfile": cfile.name,  # Client certificate
        "keyfile": kfile.name,    # Client private key
        "ca_certs": cafile.name,      # (Optional) CA certificate
    })
    print(ws.recv())
    ws.send(b'Hello')
    ws.close()
    return b"Ok"

@app.get('/test/posts',name='Run time https test',tags=['Posts','APIM'])
def run_https():
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as cfile , tempfile.NamedTemporaryFile(delete=False) as kfile, tempfile.NamedTemporaryFile(delete=False) as cafile:
        cfile.write(cc.encode()) , kfile.write(pp.encode()), cafile.write(c.encode())
        cfile.flush() , kfile.flush(), cafile.flush()
    
    resp = request('get','https://localhost:8443/posts',cert=(cfile.name, kfile.name, cafile.name),verify=cafile.name)

    return Response(resp.text, resp.status_code,resp.headers,resp.headers['content-type'])



if __name__ == "__main__":
    app.run('0.0.0.0',8000,sslport=8443,ssl=True, certfile=cc,keyfile=pp, sslpem=True,workers=4)
    