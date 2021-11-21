from enum import Enum
from random import choice
from siteclone.httphelper.request import HTTPHeader
import siteclone.paramextractor as paramextractor
import json
import socket

class ContainerType(Enum):
    Method = 0
    PathFragment = 1
    Anchor = 2
    Query = 3
    Response = 4
    
class ParameterFinder(object):
    __param_name: str
    __value_to_find: str
    
    @property
    def param(self) -> str:
        return self.__param_name
    
    @property
    def value(self) -> str:
        return self.__value_to_find
    
    def __init__(self, param: str, value: str) -> None:
        self.__param_name = param
        self.__value_to_find = value
        
    def __search_body(self, request: 'siteclone.httphelper.request.Request') -> bool:
        pos = request.body.find(self.value.encode('ascii'))
        if pos != -1:
            content_type = request.get_header(HTTPHeader.ContentType)
            if content_type is None:
                content_type = ""
            extractor = paramextractor.BodyParamExtractor.get_extractor(content_type)(request)
            return [(type(extractor), extractor.build_rule(self.value))]
        return []
        
    def __search_get_params(self, request: 'siteclone.httphelper.request.Request') -> tuple:
        pos = str(request.url).find(self.value)
        if pos != -1:
            extractor = paramextractor.QueryStringExtractor(request)
            return [(type(extractor), extractor.build_rule(self.value))]
        return []
        
    def search_request(self, request: 'siteclone.httphelper.request.Request') -> list[tuple]:
        results = []
        results += self.__search_body(request)
        results += self.__search_get_params(request)
        if len(results) > 0:
            for extractor_type, extractor_rule in results:
                print(f"[*] Using extractor '{extractor_type.__name__}' with rule '{extractor_rule}' for param '{self.param}'.")
        return results
        

class Container(object):
    ReflectionSeparator = "___P___"
    __response: 'siteclone.httphelper.response.Response'
    __reflections: list[str]
    
    @property
    def children(self):
        return self.__children
        
    @property
    def has_children(self):
        return self.__children is not None
        
    @property
    def response(self) -> 'siteclone.httphelper.response.Response':
        return self.__response
        
    @property
    def extractors_info(self):
        return self.__extractors_info
    
    @property
    def is_terminal(self) -> bool:
        return self.__response is not None
    
    @property
    def is_output(self) -> bool:
        return len(self.__extractors_info) > 0

    def __init__(self) -> None:
        self.__children = None
        self.__response = None
        self.__extractors_info = {}
        
    def goto(self, key, container_type: 'ContainerType', create_on_miss: bool = False) -> 'Container':
        if self.__children is None:
            self.__children = {}
        full_key = (container_type, key)
        if full_key not in self.children:
            if create_on_miss:
                self.children[full_key] = Container()
            else:
                raise KeyError()
        child = self.children[full_key]
        return child
        
    def put_response(self, response: 'siteclone.httphelper.response.Response') -> None:
        self.__response = response
    
    def __apply_param_reflection(self, param_finder: 'ParameterFinder') -> bool:
        if not self.is_terminal:
            raise ValueError("Couldn't apply param reflection to a non terminal node")
        encoded_value = param_finder.value.encode("ascii")
        reflection_found = False
        
        # search reflection in response content
        if self.response.content.find(encoded_value) != -1:
            self.response.content = self.response.content.replace(encoded_value, f"{Container.ReflectionSeparator}{param_finder.param}{Container.ReflectionSeparator}".encode("ascii"))
            reflection_found = True
        
        # search reflections in header values
        for header in self.response.headers:
            header_value = self.response.headers[header]
            if header_value.find(param_finder.value) != -1:
                self.response.headers[header] = header_value.replace(param_finder.value, f"{Container.ReflectionSeparator}{param_finder.param}{Container.ReflectionSeparator}")
                reflection_found = True
            
        return reflection_found
    
    def put_extractor(self, param_finder: 'ParameterFinder', extractor_type: type, extractor_rule: str) -> None:
        is_reflected = self.__apply_param_reflection(param_finder)
        if param_finder.param not in self.__extractors_info:
            self.__extractors_info[param_finder.param] = []
        
        self.__extractors_info[param_finder.param].append((extractor_type, extractor_rule, is_reflected))
        self.__extractors_info[param_finder.param] = sorted(self.__extractors_info[param_finder.param], key=lambda t: paramextractor.ParamExtractor.extractor_priority(t[0]))
        
    def get_response_content(self, request: 'siteclone.httphelper.request.Request') -> bytes:
        content = self.response.content
        for param in self.extractors_info:
            for extractor_type, extractor_rule, is_reflected in self.extractors_info[param]:
                if is_reflected:
                    pattern = f"{Container.ReflectionSeparator}{param}{Container.ReflectionSeparator}".encode("ascii")
                    extractor = extractor_type(request)
                    value = extractor.extract(extractor_rule)
                    content = content.replace(pattern, value.encode('ascii'))
        return content
        
    def get_response_header(self, name: str, request: 'siteclone.httphelper.request.Request') -> str:
        header_value = self.response.get_header(name)
        if header_value is None:
            return None
        if header_value.find(Container.ReflectionSeparator) != -1:
            for param in self.extractors_info:
                for extractor_type, extractor_rule, is_reflected in self.extractors_info[param]:
                    pattern = f"{Container.ReflectionSeparator}{param}{Container.ReflectionSeparator}"
                    extractor = extractor_type(request)
                    value = extractor.extract(extractor_rule)
                    header_value = header_value.replace(pattern, value)
        return header_value
        

class SiteMap(object):
    Alphabet = "abcdef0123456789"
    RandomValueLength = 12
    
    @staticmethod
    def generate_random_string(length: int) -> str:
        return ''.join([choice(SiteMap.Alphabet) for _ in range(length)])

    __site_map: 'Container'
    __domain: str = ""
    __ip_list: list[str] = None
    __username_finder: 'ParameterFinder'
    __password_finder: 'ParameterFinder'
    
    @property
    def username_finder(self) -> 'ParameterFinder':
        return self.__username_finder
    
    @property
    def password_finder(self) -> 'ParameterFinder':
        return self.__password_finder
        
    @property
    def site_map(self) -> 'Container':
        return self.__site_map
        
    def __resolve_domain(self) -> None:
        try:
            domain_info = socket.gethostbyname_ex(self.__domain)
        except socket.gaierror:
            raise ValueError("Couldn't resolve site domain")
        self.__ip_list = domain_info[2]
        
    @property
    def domain(self) -> str:
        return self.__domain
    
    @property
    def ip_list(self) -> list[str]:
        return self.__ip_list

    def __init__(self, domain: str) -> None:
        self.__site_map = Container()
        self.__domain = domain
        self.__resolve_domain()
        random_password = random_username = ""
        while random_password == random_username:
            random_password = SiteMap.generate_random_string(SiteMap.RandomValueLength)
            random_username = SiteMap.generate_random_string(SiteMap.RandomValueLength)
        self.__username_finder = ParameterFinder("username", random_username)
        self.__password_finder = ParameterFinder("password", random_password)
        
    def __locate_container(self, request: 'siteclone.httphelper.request.Request', create_on_miss: bool = False) -> 'Container':
        cur_container = self.__site_map.goto(request.method, ContainerType.Method, create_on_miss)
        for fragment in request.url.path.fragments:
            cur_container = cur_container.goto(fragment, ContainerType.PathFragment, create_on_miss)
        if request.url.path.has_anchor:
            cur_container = cur_container.goto(request.url.path.anchor, ContainerType.Anchor, create_on_miss)
        cur_container = cur_container.goto(request.url.params_set, ContainerType.Query, create_on_miss)
        return cur_container
        
    def add_entry(self, request: 'siteclone.httphelper.request.Request', response: 'siteclone.httphelper.response.Response') -> 'Container':
        container = self.__locate_container(request, True)
        container.put_response(response)
        
        username_extractors = self.username_finder.search_request(request)
        for extractor_type, extractor_rule in username_extractors:
            container.put_extractor(self.username_finder, extractor_type, extractor_rule)
        password_extractors = self.password_finder.search_request(request)
        for extractor_type, extractor_rule in password_extractors: 
            container.put_extractor(self.password_finder, extractor_type, extractor_rule)
        return container
        
    def get_entry(self, request: 'siteclone.httphelper.request.Request') -> 'siteclone.httphelper.response.Response':
        create_on_miss = False
        try:
            cur_container = self.__site_map.goto(request.method, ContainerType.Method, create_on_miss)
            for fragment in request.url.path.fragments:
                cur_container = cur_container.goto(fragment, ContainerType.PathFragment, create_on_miss)
            if request.url.path.has_anchor:
                cur_container = cur_container.goto(request.url.path.anchor, ContainerType.Anchor, create_on_miss)
        except KeyError:
            return None
        try:
            cur_container = cur_container.goto(request.url.params_set, ContainerType.Query, create_on_miss)
        except KeyError:
            # hack. TODO: replace with proper leaves merging.
            query_leaves = [item[1] for item in cur_container.children.items() if item[1].is_terminal and item[0][0] == ContainerType.Query and request.url.params_match(item[0][1])]
            if len(query_leaves) == 0: return None
            return query_leaves[0]
        return cur_container
        
    def __to_json(self):
        result = {}
        stack = [(self.__site_map, result)]
        while len(stack) > 0:
            cur_container, cur_node = stack.pop()
            #if cur_container.is_terminal:
            #    cur_node["response"] = cur_container.response.headers
            if cur_container.has_children:
                for child_key in cur_container.children:
                    if child_key[0] == ContainerType.Response:
                        out_key = f"{str(child_key[0])}__{len(child_key[1])}"
                    else:
                        out_key = f"{str(child_key[0])}__{child_key[1]}"
                    cur_node[out_key] = {}
                    stack.append((cur_container.children[child_key], cur_node[out_key]))
        return result
    
    def __to_string(self) -> str:
        return json.dumps(self.__to_json(), indent=4)
        
    def __str__(self) -> str:
        return self.__to_string()
        
    def __repr__(self) -> str:
        return self.__to_string()
        
        