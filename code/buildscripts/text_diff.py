import re

_WHITESPACE_PAT = re.compile(unicode(r'\s+'))

def texts_differ(a, b):
    '''
    Default comparison function used in diff() and write_if_different(). Just uses
    python's built-in cmp(str1, str2).
    '''
    return cmp(a, b) != 0

def texts_differ_ignore_case(a, b):
    '''
    Compares text ignoring case.
    '''
    return cmp(a.lower(), b.lower()) != 0

def texts_differ_ignore_whitespace(a, b):
    '''
    Compares text ignoring case.
    '''
    a = _WHITESPACE_PAT.sub(u'', a)
    b = _WHITESPACE_PAT.sub(u'', b)
    x = cmp(a, b)
    return x != 0

def texts_differ_ignore_case_and_whitespace(a, b):
    '''
    Compares text ignoring case and whitespace.
    '''
    a = _WHITESPACE_PAT.sub(u'', a).lower()
    b = _WHITESPACE_PAT.sub(u'', b).lower()
    return cmp(a, b) != 0

