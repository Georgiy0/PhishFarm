from urllib.parse import urlparse as parseurl, parse_qs

class UrlPath(object):
    __raw_path: str = ""
    __fragments: list[str] = []
    __anchor: str = ""
    
    @property
    def fragments(self) -> list[str]:
        return self.__fragments
    
    @property
    def anchor(self) -> str:
        return self.__anchor
        
    @property
    def has_anchor(self) -> bool:
        return len(self.__anchor) > 0
    
    def __init__(self, raw_path) -> None:
        self.__raw_path = raw_path
        path_anchor_split = self.__raw_path.split("#")
        self.__fragments = path_anchor_split[0].split("/")
        if len(path_anchor_split) > 1:
            self.__anchor = "#" + "#".join(path_anchor_split[1:])
            
    def __to_string(self) -> str:
        return self.__raw_path
        
    def __str__(self) -> str:
        return self.__to_string()
        
    def __repr__(self) -> str:
        return self.__to_string()
            
            
class Url(object):
    __raw_url: str = ""
    __host: str = ""
    __get_params: dict[str, list[str]] = {}
    __path: 'UrlPath'
    __anchor: str = ""
    
    @property
    def host(self) -> str:
        return self.__host
    
    @property
    def anchor(self) -> str:
        return self.__anchor
        
    @property
    def path(self) -> 'UrlPath':
        return self.__path
        
    @property
    def params_set(self) -> tuple:
        result = []
        for param in self.__get_params:
            for value in self.__get_params[param]:
                result.append((param, value))
        return tuple(sorted(result, key=lambda p: f"{p[0]}_{p[1]}"))
    
    @property
    def get_params(self) -> dict[str, list[str]]:
        return self.__get_params
        
    def params_match(self, other: tuple) -> bool:
        return set([elem[0] for elem in self.params_set]) == set([elem[0] for elem in other])
        
    def __parse_url(self) -> None:
        pr = parseurl(self.__raw_url, allow_fragments=False)
        __host = pr.netloc
        if pr.query:
            self.__get_params = parse_qs(pr.query)
        self.__path = UrlPath(pr.path)
        
    def __init__(self, raw_url: str) -> None:
        self.__raw_url = raw_url
        self.__parse_url()
        
    def __to_string(self) -> str:
        return self.__raw_url
        
    def __str__(self) -> str:
        return self.__to_string()
        
    def __repr__(self) -> str:
        return self.__to_string()
        
        
class HTTPHeader(object):
    ContentType = "Content-Type"
    Location = "Location"

class Request(object):
    __method: str = ""
    __headers: dict[str, str] = {}
    __url: 'Url' = None
    __body: bytes = b''
    
    @property
    def method(self) -> str:
        return self.__method
        
    @property
    def headers(self) -> dict[str, list[str]]:
        return self.__headers
        
    @property
    def url(self) -> 'Url':
        return self.__url
    
    @property
    def body(self) -> bytes:
        return self.__body
        
    def get_header(self, name) -> str:
        if name in self.headers:
            return self.headers[name]
        elif name.lower() in self.headers:
            return self.headers[name.lower()]
        else:
            return None

    def __init__(self, method: str, url: str, body: bytes, headers: dict[str, str]) -> None:
        self.__method = method
        self.__url = url
        self.__body = body
        self.__headers = headers
    
    @classmethod
    def from_mp_request(cls, mp_req: 'mitmproxy.net.http.request.Request'):
        url = Url(mp_req.url)
        method = mp_req.method
        body = mp_req.content
        headers = {}
        for header in mp_req.headers:
            headers[header] = mp_req.headers[header]
        return cls(method, url, body, headers)
            
    @classmethod
    def from_tornado_request(cls, tornado_req: 'tornado.httputil.HTTPServerRequest') -> None:
        url = Url(tornado_req.full_url())
        method = tornado_req.method
        body = tornado_req.body
        headers = {}
        for header in tornado_req.headers:
            headers[header] = tornado_req.headers[header]
        return cls(method, url, body, headers)    
        
    def __to_string(self) -> str:
        headers_out = '\n\t\t'.join([f'{header}: {self.headers[header]}' for header in self.headers])
        return f"{self.method} {self.url}\n\tHeaders\n\t\t{headers_out}\n\tBody length: {len(self.body)}"
        
    def __str__(self) -> str:
        return self.__to_string()
        
    def __repr__(self) -> str:
        return self.__to_string()
