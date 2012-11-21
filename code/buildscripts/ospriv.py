import os
import subprocess
import check_output

_ADMINPRIV = None
def user_has_admin_privileges():
    global _ADMINPRIV
    if os.name == 'nt':
        if _ADMINPRIV is None:
            try:
                stdout = subprocess.check_output("whoami /priv", shell=True)
                _ADMINPRIV = stdout.find("SeCreateGlobalPrivilege") > -1
            except CalledProcessError:
                _ADMINPRIV = False
    else:
        if _ADMINPRIV is None:
            _ADMINPRIV = (os.getegid() == 0)
    return _ADMINPRIV

