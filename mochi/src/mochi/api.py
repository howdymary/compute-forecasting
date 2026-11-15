from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .simulation import ROOT

app=FastAPI(title='Mochi · Robot Research Lab')
@app.get('/api/health')
def health():return {'status':'ok','mode':'recorded physics replay','service':'mochi'}
app.mount('/',StaticFiles(directory=ROOT/'web',html=True),name='web')
