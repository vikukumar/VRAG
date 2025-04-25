from lib import Router

auth = Router(prefix='/auth/v1',tags=['Auth'])

@auth.get('/test',name='Mehtods')
async def test():
    return {'message': 'Working'}