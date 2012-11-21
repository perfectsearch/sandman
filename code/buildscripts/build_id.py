from collections import namedtuple

def build_id_from_str(txt):
    # Expect something like this: sadm.trunk.137.20. We have to be a bit
    # careful, because branch names can contain dots. This means we can't
    # just split on .
    i = txt.find('.')
    c = txt[0:i]
    txt = txt[i+1:]
    if (txt.count('.') >= 4):
        i = txt.rfind('.')
        date = txt[i + 1:]
        txt = txt[0:i]
        i = txt.rfind('.')
        guid = txt[i + 1:]
        txt = txt[0:i]
    else:
        guid = ''
        date = ''
    i = txt.rfind('.')
    tr = int(txt[i + 1:])
    txt = txt[0:i]
    i = txt.rfind('.')
    cr = int(txt[i + 1:])
    b = txt[0:i]
    return BuildID(c, b, cr, tr, guid, date)

def _cmp(self, other):
    # Allow comparison to string version of the tuple as well as object version.
    if hasattr(other, 'lower'):
        other = build_id_from_str(other)
    i = cmp(self.component.lower(), other.component.lower())
    if not i:
        i = cmp(self.branch.lower(), other.branch.lower())
        if not i:
            i = cmp(self.code_revno, other.code_revno)
            if not i:
                i = cmp(self.test_revno, other.test_revno)
                if not i:
                    i = cmp(self.guid, other.guid)
                    if not i:
                        i = cmp(self.date, other.date)
    return i

# We want a BuildID class that behaves like a tuple, except that it serializes
# and compares with slightly more sophistication.
BuildID = namedtuple('BuildID', 'component branch code_revno test_revno guid date')
# Override how BuildID serializes...
BuildID.__str__ = lambda bid: '%s.%s.%d.%d.%s.%s' % bid
# Override how BuildID compares...
BuildID.__cmp__ = _cmp
# Remove the publicly visible standalone func, leaving only the member method.
del(_cmp)
# Also override __eq__
BuildID.__eq__ = lambda self, other: self.__cmp__(other) == 0
