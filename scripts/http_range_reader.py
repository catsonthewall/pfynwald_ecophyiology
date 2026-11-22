"""Verified-TLS urllib range reader for rasterio's opener interface.

This adapter is useful when a bundled GDAL/libcurl build cannot discover the
environment's CA certificate configuration. It keeps normal TLS verification
and uses the same public URL, proxy and authorized read token as urllib.
It never disables checks, alters routing, or downloads a full COG fallback.
"""
import io
import re
import urllib.request


class HTTPRangeReader(io.RawIOBase):
    def __init__(self,url,block_size=262144):
        self.url=url; self.block_size=block_size;self.pos=0;self.cache={}
        # Read a bounded first block, extracting true content length.
        data,total=self._request(0,block_size-1)
        self.length=total;self.cache[0]=data

    def _request(self,start,end):
        req=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}'})
        with urllib.request.urlopen(req,timeout=60) as r:
            if r.status!=206:
                raise IOError(f'Server did not honour bounded Range request: {r.status}')
            cr=r.headers.get('Content-Range','')
            match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',cr)
            if not match or int(match[1])!=start:
                raise IOError('Unexpected Content-Range response')
            data=r.read(end-start+2)
            if len(data)>end-start+1:
                raise IOError('Range response exceeded requested bytes')
            return data,int(match[3])

    def read(self,n=-1):
        if n is None or n<0:
            # Guard against accidentally reading an entire full-resolution tile.
            raise IOError('Unbounded remote reads are disabled; use rasterio opener')
        n=min(n,self.length-self.pos)
        if n<=0:return b''
        result=[]
        while n:
            block=self.pos//self.block_size;offset=self.pos%self.block_size
            if block not in self.cache:
                start=block*self.block_size
                self.cache[block]=self._request(start,min(start+self.block_size-1,self.length-1))[0]
            chunk=self.cache[block][offset:offset+n]
            if not chunk:break
            result.append(chunk);self.pos+=len(chunk);n-=len(chunk)
        return b''.join(result)

    def readinto(self,b):
        d=self.read(len(b));b[:len(d)]=d;return len(d)

    def seek(self,offset,whence=io.SEEK_SET):
        if whence==io.SEEK_SET:self.pos=offset
        elif whence==io.SEEK_CUR:self.pos+=offset
        elif whence==io.SEEK_END:self.pos=self.length+offset
        else:raise ValueError('invalid whence')
        if self.pos<0:raise ValueError('negative seek')
        return self.pos

    def tell(self):return self.pos
    def seekable(self):return True
    def readable(self):return True
