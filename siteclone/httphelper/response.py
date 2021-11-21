class Response(object):
    __headers: dict[str, str]
    __content: bytes
    __status: int

    @property
    def headers(self) -> dict[str, list[str]]:
        return self.__headers
        
    def get_header(self, name: str) -> str:
        if name in self.headers:
            return self.headers[name]
        elif name.lower() in self.headers:
            return self.headers[name.lower()]
        else:
            return None
    
    @property
    def content(self) -> bytes:
        return self.__content
        
    @content.setter
    def content(self, value: bytes) -> None:
        self.__content = value
        
    @property
    def status(self) -> int:
        return self.__status

    def __init__(self, mp_resp: 'mitmproxy.net.http.response.Response') -> None:
        self.__headers = {}
        self.__content = b""
        self.__status = 0
    
        self.__content = mp_resp.content
        self.__status = mp_resp.status_code
        for header in mp_resp.headers:
            self.__headers[header] = mp_resp.headers[header]
        
    def __to_string(self) -> str:
        headers_out = '\n\t\t'.join([f'{header}: {self.headers[header]}' for header in self.headers])
        return f"{self.status}\n\tHeaders{headers_out}\n\tContent length: {len(self.content)}"
        
    def __str__(self) -> str:
        return self.__to_string()
        
    def __repr__(self) -> str:
        return self.__to_string()
        
        