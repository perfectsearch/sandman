# List all ant build.xml files in the sandbox that should be called by the
# build system.

import os
import sandbox
import ioutil
import sys

if __name__ == '__main__':
    if 'True' in sys.argv:
        quick = True
    else:
        quick = False
    x = []
    try:
        sb = sandbox.current
        deps = [l.name for l in sb.get_cached_components()]
        x = []
        for c in deps:
            if 'code' in sb.get_component_aspects(c):
                path = sb.get_code_root() + c + '/build.xml'
            else:
                path = sb.get_built_root() + c + '/build.xml'
            if os.path.isfile(path):
                if quick and path.find('built.') > -1:
                    continue
                x.append(path)
    except:
        pass
    print(','.join(x))
