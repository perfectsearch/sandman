#!/usr/bin/env python
# 
# $Id: martian.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
import random, re

_SUBST = {
    'a': [u'a',u'\u00e1',u'\u00e2',u'\u00e3',u'\u00e5',u'\u0430',u'\u0410',u'\u0391',u'\u0386',u'\u03ac',u'\u03b1',u'\u30e0',u'\u30aa',u'\u11ba'],
    'e': [u'e',u'\u0415',u'\u0435',u'\u042d',u'\u044d',u'\u0388',u'\u0395',u'\u03b5',u'\u03f5',u'\u03f6',u'\u30e7'],
    'i': [u'i',u'\u0407',u'\uff74',u'\u0456',u'\u0457',u'\u03b9',u'\u03af',u'\u03ca',u'\u30a7',u'\u0671'],
    'o': [u'o',u'\u03bf',u'\u03cc',u'\uff9b',u'\u00f5',u'\u00f4',u'\u03d9',u'\u1f42',u'\u1f48',u'\u041e',u'\u043e',u'\u30ed',u'\u05e1',u'\u0ae6'],
    'u': [u'u',u'\u00b5',u'\u00fa',u'\u00fb',u'\u00fc',u'\u03c5',u'\u03cb',u'\u03cd',u'\u03b0',u'\u0646'],
    's': [u's',u'$',u'\u0abd',u'\uff53'],
    't': [u't',u'\u03ee',u'\uff34'],
    'b': [u'b',u'\u03d0',u'\u00df',u'\uff42'],
    'n': [u'n',u'\u00f1'],
}

WORD_PAT = re.compile(u"[a-z]+['a-z][a-z]+", re.IGNORECASE)
UNICODE_TYPE = type(u'')

def endsWithVowel(word):
    return u'aeiou'.find(word[-1]) > -1

def convertWord(word):
    # Always randomize based on length of word, so that same words get same form.
    # This helps to keep the converted forms of complete text files stable as some
    # strings are added and subtracted.
    r = random.Random(len(word))
    startIdx = 0
    word2 = u''
    # Keep initial caps
    if word[0] == word[0].upper():
        word2 = word[0]
        startIdx = 1
    # Substitute chars that are visually similar
    for i in range(startIdx, len(word)):
        c = word[i]
        if c in _SUBST:
            alts = _SUBST[c]
            word2 = word2 + alts[r.randint(0, len(alts) - 1)]
        elif i % 2 == 0:
            word2 = word2 + c.upper()
        else:
            word2 = word2 + c.lower()
    # Make words longer, on average, than English.
    wordLen = len(word)
    if endsWithVowel(word):
        justChar = u'h'
    else:
        justChar = word2[-1]
    if wordLen < 5:
        word2 = word2 + justChar
    else:
        extra = r.randint(0, int(max(.5 * wordLen, 3)))
        word2 = word2 + u''.rjust(extra, justChar)
    return word2

def convert(txt):
    if type(txt) != UNICODE_TYPE:
        txt = unicode(str(txt), 'utf-8')
    # Replace some spaces with x to make words longer (tests whether
    # layout handles word wrapping in a flexible and reasonable way).
    i = 0
    n = 0
    while True:
        i = txt.find(u' ', i)
        if i == -1:
            break
        # Do a substitution every third word
        if (i > 0) and (i < len(txt) - 1) and txt[i-1].isalpha() and txt[i+1].isalpha():
            if n % 3 == 1:
                txt = txt[0:i] + u'X' + txt[i+1:]
            n = n + 1
        elif n % 3 != 1:
            n = n + 1
        i = i + 1
    output = u''
    while True:
        m = WORD_PAT.search(txt)
        if not m:
            break
        output = output + txt[0:m.start()]
        output = output + convertWord(m.group(0))
        txt = txt[m.end():]
    output += txt
    # Always put hash marks at beginning and end, so we can easily tell
    # if the full string is displayed or only a partial string.
    # Ignore @@ comments.
    if output.find('@@') > -1:
        return u'#' + output[:output.find('@@')] + u'#' + output[output.find('@@'):]
    return u'#' + output + '#'

if __name__ == '__main__':
    print(convert("almost, this is a test"))
    print(convert("&Open"))
    print(convert("&Close"))
    print(convert("&Next"))
    print(convert("The quick brown fox, jumped (smoothly) over the small red dog."))
    print(convert("""This is a paragraph of text.
        I hope that it all converts smoothly.
        The quick brown fox, jumped (smoothly) over the small striped red dog."""))
