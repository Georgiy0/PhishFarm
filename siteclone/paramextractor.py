from abc import ABC, abstractmethod
from urllib.parse import parse_qs

class ParamExtractor(ABC):
    __request: 'siteclone.httpheper.request.Request'
    
    @staticmethod
    def extractor_priority(extractor):
        cls = type(extractor)
        if issubclass(cls, BodyParamExtractor): return 0
        elif isinstance(cls, QueryStringExtractor): return 1
        else: return 100
    
    @property
    def request(self) -> 'siteclone.httphelper.request.Request':
        return self.__request
    
    def __init__(self, request) -> None:
        self.__request = request
        
    @abstractmethod
    def build_rule(self, value: str) -> str:
        pass
        
    @abstractmethod
    def extract(self, rule: str) -> str:
        pass
        

class QueryStringExtractor(ParamExtractor):
    def build_rule(self, value: str) -> str:
        for param in self.request.url.get_params:
            if value in self.request.url.get_params[param]:
                return param
        raise NotImplementedError("Couldn't locate value in query parameters")
        
    def extract(self, rule: str) -> str:
        if rule not in self.request.url.get_params:
            raise NotImplementedError("Couldn't extract")
        values = self.request.url.get_params[rule]
        if len(values) > 1:
            raise NotImplementedError("Couldn't extract")
        return values[0]
        

class BodyParamExtractor(ParamExtractor):
    @staticmethod
    def accept_content_type(content_type: str) -> bool:
        return False
        
    @staticmethod
    def get_extractor(content_type: str):
        extractors = [cls for name, cls in globals().items() if isinstance(cls, type) and not isinstance(cls, BodyParamExtractor) and issubclass(cls, BodyParamExtractor) and cls.accept_content_type(content_type)]
        if len(extractors) == 1:
            return extractors[0]
        elif len(extractors) == 0:
            # use default extractor
            return BodyParamExtractor
        elif len(extractors) > 1:
            raise ValueError(f"More than one extractor for {content_type}")
            
    def build_rule(self, value: str) -> str:
        return ""
        
    def extract(self, rule: str) -> str:
        return self.request.body.decode("utf-8")

    
class PostDataParamExtractor(BodyParamExtractor):
    @staticmethod
    def accept_content_type(content_type) -> bool:
        return content_type.lower() == "application/x-www-form-urlencoded"
    
    def __parse_params(self) -> dict[str, list[str]]:
        post_data = self.request.body.decode("utf-8")
        return parse_qs(post_data)
    
    def build_rule(self, value: str) -> str:
        parsed_data = self.__parse_params()
        for param_name in parsed_data:
            if value in parsed_data[param_name]:
                return param_name
        raise NotImplementedError("Couldn't locate value in post data")
        
    def extract(self, rule: str) -> str:
        params = self.__parse_params()
        if rule not in params:
            raise NotImplementedError("Couldn't extract")
        return params[rule][0]
        
        