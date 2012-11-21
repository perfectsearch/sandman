import os

_added = False
if not _added:
    _added = True
    import sys
    my_folder = os.path.dirname(os.path.abspath(__file__))
    # Sadm can get buildscripts from one of three different places. In
    # production, it expects a buildscripts folder that's a sibling of sadm.py.
    # In development, it can find code/buildscripts, or built/buildscripts.any.
    # We need to add the correct version to sys.path.
    loc = os.path.abspath(os.path.join(my_folder, '..', 'buildscripts'))
    if not os.path.isdir(loc):
        # Try code root. Code should always override prebuilt stuff.
        loc = os.path.abspath(os.path.join(my_folder, '..', '..', 'buildscripts'))
        assert(os.path.isdir(loc))
    # We have to put our path at the front of the paths instead of the end,
    # because some python distros have a package named "test" which would
    # possibly cause an incorrect import of the test.py in buildscripts.
    sys.path.insert(0, loc)
    del(my_folder)
    del(loc)

__all__ = [x[0:-3] for x in os.listdir(os.path.dirname(os.path.abspath(__file__))) if x.startswith('sadm_') and x.endswith('.py')]
__all__.sort()
