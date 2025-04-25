from .globals import APP , Process, PROCESS

def startMP(*args, **kwargs):
    worker:int = 1
    if 'workers' in kwargs:
        worker = int(kwargs.pop('workers'))

    if 'Main' in APP:
        app = APP['Main']

    print(app)

    for i in range(1, worker+1):
        p = Process(name=f'Worker {i}',target=app.run,args=(*args,),kwargs={**kwargs,})
        p.start()
        PROCESS.append(p)

    
    for p in PROCESS:
        p.join()



