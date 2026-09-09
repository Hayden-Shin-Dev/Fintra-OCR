"""Read-only Azure ZIP member retrieval; OAuth token stays in process memory.
Uses Get Blob byte ranges: https://learn.microsoft.com/rest/api/storageservices/get-blob
"""
import io,json,subprocess,zipfile,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
AZ=r'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
_token=None
def token():
 global _token
 if _token is None or time.time()-_token[0]>1800:
  r=subprocess.run([AZ,'account','get-access-token','--resource','https://storage.azure.com/','-o','json'],capture_output=True,check=True)
  _token=(time.time(),json.loads(r.stdout)['accessToken'])
 return _token[1]
class BlobReader(io.RawIOBase):
 def __init__(self,blob):
  self.blob=blob;self.size=blob['properties']['contentLength'];self.pos=0;self.cache_start=0;self.cache=b''
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):
  self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
  if self.pos<0:raise ValueError('Negative seek')
  return self.pos
 def read(self,n=-1):
  if n<0:n=self.size-self.pos
  n=min(n,self.size-self.pos)
  if n<=0:return b''
  if not self.cache_start<=self.pos or self.pos+n>self.cache_start+len(self.cache):
   end=min(self.size-1,self.pos+max(n,131072)-1)
   headers={'Authorization':'Bearer '+token(),'x-ms-version':'2023-11-03','Range':f'bytes={self.pos}-{end}','If-Match':self.blob['properties']['etag']}
   url='https://stfintradevkrc.blob.core.windows.net/fintra/'+quote(self.blob['name'],safe='/')
   with urlopen(Request(url,headers=headers),timeout=90) as response:
    if response.status!=206:raise RuntimeError('Expected byte range response')
    self.cache=response.read();self.cache_start=self.pos
  out=self.cache[self.pos-self.cache_start:self.pos-self.cache_start+n];self.pos+=len(out);return out
def blobs():return json.loads((ROOT/'outputs/acceptance/azure-inventory.json').read_text(encoding='utf-8'))
def labels():
 out=ROOT/'data/acceptance/labels';out.mkdir(parents=True,exist_ok=True)
 for b in blobs():
  if '/Validation/02.' not in b['name'] or not any('_'+code in b['name'] for code in ['INV','PL','BL']):continue
  tag=b['name'].rsplit('_',1)[1].removesuffix('.zip')
  dest=out/(tag+'.zip')
  if not dest.exists():dest.write_bytes(BlobReader(b).read())
  with zipfile.ZipFile(dest) as z:
   names=[n for n in z.namelist() if n.endswith('.json')]
   first=json.loads(z.read(names[0]));print(tag,len(names),names[0],json.dumps(first,ensure_ascii=True)[:5000],flush=True)
if __name__=='__main__':labels()
