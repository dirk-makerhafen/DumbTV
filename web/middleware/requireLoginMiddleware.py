from django.http import HttpResponseRedirect
from django.conf import settings
from re import compile
 
EXEMPT_URLS = [compile(settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]
 
class LoginRequiredMiddleware :
    def __init__(self, get_response = None): # django 1/2 compatible
        self.get_response = get_response

    def __call__(self, request):
        return self.process_request(request)
        
    def process_request(self, request):
        try:
            is_authenticated = request.user.is_authenticated()
        except:
            is_authenticated = request.user.is_authenticated
        if not is_authenticated:
            path = request.path_info.lstrip('/')
            if not any(m.match(path) for m in EXEMPT_URLS):
                return HttpResponseRedirect(settings.LOGIN_URL)
        if self.get_response != None: # django 1/2 compatible
            response = self.get_response(request)
            return response
