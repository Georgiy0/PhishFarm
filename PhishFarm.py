from siteclone.httphelper import Request, Response
from siteclone import SiteMap
import pickle
from mitmproxy import command
from mitmproxy import ctx

class SiteCloningAddon(object):
    __site_map: 'siteclone.SiteMap' = None
    
    @property
    def site_map(self) -> 'siteclone.SiteMap':
        return self.__site_map
        
    @site_map.setter
    def site_map(self, value: 'siteclone.SiteMap') -> None:
        if self.__site_map is None:
            self.__site_map = value

    def __init__(self) -> None:
        self.__site_map = None
        
    def load(self, loader):
        loader.add_option(
            name = "clonedomain",
            typespec = str,
            default = "localhost",
            help = "Domain of the site to be cloned",
        )
        
    def __is_in_scope(self, url: str) -> bool:
        for ip in self.__site_map.ip_list:
            return url.find(ip) != -1
        return False
        
    def response(self, flow) -> None:
        if self.site_map is None:
            domain = ctx.options.clonedomain
            if domain is None:
                print(f"[!] Missing option 'clonedomain'")
                return
            self.site_map = SiteMap(ctx.options.clonedomain)
            print(f"[*] Clonning domain '{self.site_map.domain}'")
            print(f"[*] Use username: {self.site_map.username_finder.value}")
            print(f"[*] Use password: {self.site_map.password_finder.value}")
    
        if self.__is_in_scope(flow.request.url):
            request = Request.from_mp_request(flow.request)
            print(f"[*] Processing {request.url}")
            response = Response(flow.response)
            entry = self.site_map.add_entry(request, response)
            if entry.is_output:
                params = list(entry.extractors_info.keys())
                print(f"[+] Built extractors for parameters: {', '.join(params)}")
        self.save()
        
    def save(self) -> None:
        filename = f"{self.site_map.domain}.sm"
        with open(filename, "wb") as file_out:
            pickle.dump(self.site_map, file_out)
        open("sitemap.txt", "w").write(str(self.site_map))


addons = [
    SiteCloningAddon()
]