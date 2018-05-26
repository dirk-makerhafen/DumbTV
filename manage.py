#!/usr/bin/env python
import os
import sys
import sys
try:
    reload(sys)  # Reload does the trick!
    sys.setdefaultencoding('UTF8')
except:
    pass
    
sys.dont_write_bytecode = True

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/kodino" ))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
