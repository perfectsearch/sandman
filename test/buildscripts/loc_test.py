#!/usr/bin/env python
# -*- coding: utf8 -*-
# $Id: CodeStatTest.py 4165 2010-12-30 12:04:29Z dhh1969 $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#

import unittest, sys, os
from l10n.loc import *
from codescan.codescan import *
from l10n.locdata import findMisses, pureHTML
from testsupport import checkin, officialbuild

_MATCHTYPE = type(re.compile('x').match('x'))

@officialbuild
class LocTest(unittest.TestCase):
    def _checkMatch(self, m):
        if m:
            self.assertEquals(_MATCHTYPE, type(m))
        else:
            self.fail('Expected a match; got None.')
    def assertMatch(self, value, match, grp=0):
        self._checkMatch(match)
        self.assertEquals(value, match.group(grp))
    def assertMatches(self, match, *values):
        self._checkMatch(match)
        values = str(values)
        grps = str(match.groups())
        self.assertEquals(values, grps)
    def test_GETTEXT_PAT(self):
        txt = """
        x = gettext("abc");
        not_a_callgettext("ABC");
        not_a_call = _();
        another_not_a_call_because_it_spans_lines = gettext("hello
            dolly");
        y = _ ( 'def' );
        z =_("a test \\") of our escape handling and 'nested' stuff");
        """
        matches = [m for m in GETTEXT_PAT.finditer(txt)]
        self.assertMatch('gettext("abc")', matches[0])
        self.assertMatch("_ ( 'def' )", matches[1])
        self.assertMatch('_("a test \\") of our escape handling and \'nested\' stuff")', matches[2])
    def test_NOTE_PAT(self):
        m = NOTE_PAT.match('this is a string@@and this is a note')
        self.assertMatches(m, 'this is a string', 'and this is a note')
    def test_STRINGSFILE_PAT(self):
        m = STRINGSFILE_PAT.match("strings-en_US.txt")
        self.assertMatches(m, None, 'en_US', 'txt')
        m = STRINGSFILE_PAT.match("FOOstrings-fr.js")
        self.assertMatches(m, 'FOO', 'fr', 'js')
        m = STRINGSFILE_PAT.match("x-strings-zh_TW.txt.py")
        self.assertMatches(m, 'x-', 'zh_TW', 'txt.py')
    def test_CANONICAL_STRINGSFILE_PAT(self):
        m = CANONICAL_STRINGSFILE_PAT.match("Strings-en_US.txt")
        self.assertFalse(bool(m))
        m = CANONICAL_STRINGSFILE_PAT.match("strings-en_US.txt")
        self.assertMatches(m, None, 'en_US', 'txt')
        self.assertFalse(bool(CANONICAL_STRINGSFILE_PAT.match("FOOstrings-fr.js")))
        m = CANONICAL_STRINGSFILE_PAT.match("FOO-strings-fr.js")
        self.assertMatches(m, 'FOO', 'fr', 'js')
        m = CANONICAL_STRINGSFILE_PAT.match("x-strings-zh_TW.txt.py")
        self.assertMatches(m, 'x', 'zh_TW', 'txt.py')
        self.assertFalse(bool(CANONICAL_STRINGSFILE_PAT.match("x-strings-zh_TW@euro.py")))
    def test_prepForJson(self):
        self.assertEquals("foo", prepForJson("foo"))
        self.assertEquals("foo 'test'", prepForJson("foo 'test'"))
        self.assertEquals(r'foo \"test\"', prepForJson('foo "test"'))
    def test_undoEscapes(self):
        self.assertEquals("foo", undoEscapes("foo"))
        self.assertEquals("foo 'test'", undoEscapes("foo 'test'"))
        self.assertEquals(r'foo "test"', undoEscapes(r'foo \"test\"'))
    def test_FORMAT_SPEC_PAT(self):
        txt = """
        x = gettext("ab {0} c{1:date} {2}");
        not_a_callgettext("ABC");
        not_a_call = _();
        another_not_a_call_because_it_spans_lines = gettext("hello
            dolly");
        y = _ ( 'd{0}e{1:date}f {2}' );
        z =_("a test \\") of {0}our e{1:date}scape handl{2}ing and 'nested' stuff");
        """
        matches = [m for m in GETTEXT_PAT.finditer(txt)]
        for m in matches:
            specs = [m.group(0) for m in FORMAT_SPEC_PAT.finditer(m.group(0))]
            self.assertEquals('{0}', specs[0])
            self.assertEquals("{1:date}", specs[1])
            self.assertEquals('{2}', specs[2])
    def test_TRANS_PAT(self):
        txt = """
{
  vocabulary: {
    global: {
      "Refresh" : "Обновить"
    },
    foldergrid: {
    "Selected Folders": "Выбранные Папки",
    "Folder and Path": "Папка и Путь",
    "Size": "Объем",
    "Drag folders here": "Перетащите папку в эту область",
    "Size summing:": "Суммарный объем:"
    },
    folderbrowser: {
    "Add": "Добавить",
    "Delete": "Удалить",
    "Source": "Источник"
    }
  }
}"""
        matches = [m for m in TRANS_PAT.finditer(txt)]
        self.assertEqual(9, len(matches))
        self.assertEqual("Drag folders here", matches[4].group(2))
    def test_WORDSPLIT_PAT(self):
        matches = [m for m in WORDSPLIT_PAT.finditer("The quick red-haired fox, daintily (and without fanfare)--tripped over the lazy brown dog.")]
        self.assertEqual(15, len(matches))
    def test_StrDef_getWordCount(self):
        x = StrDef('x', 'This is a test', 'en')
        self.assertEqual(4, x.getWordCount())
    def test_CHECK_SHOUT(self):
        probs = CHECK_SHOUT.check('The sky is falling!', None)
        self.assertTrue(probs)
        self.assertTrue(probs.find("xclamation") > -1)
        probs = CHECK_SHOUT.check('The sky is falling!', '-w4')
        self.assertFalse(probs)
        probs = CHECK_SHOUT.check('nothing interesting here', None)
        self.assertFalse(probs)
    def test_CHECK_SEMIPLURAL(self):
        probs = CHECK_SEMIPLURAL.check('3 error(s) found', None)
        self.assertTrue(probs)
        self.assertTrue(probs.find("(s)") > -1)
        probs = CHECK_SEMIPLURAL.check('3 error(s) found', '-w13')
        self.assertTrue(probs)
        self.assertTrue(probs.find("(s)") > -1)
    def test_CHECK_OLDSTYLE_PUNCT(self):
        probs = CHECK_OLDSTYLE_PUNCT.check('A sentence.  Another one.', None)
        self.assertTrue(probs)
        self.assertTrue(probs.find("single space") > -1)
    def test_CHECK_FORMAT_SPECIFIERS(self):
        probs = CHECK_FORMAT_SPECIFIERS.check('X {1} {2}', None)
        self.assertTrue(probs)
        ptxt = str(probs)
        self.assertTrue(ptxt.find("{0}") > -1)
        probs = CHECK_FORMAT_SPECIFIERS.check('X {0} {222}', None)
        self.assertTrue(probs)
        ptxt = str(probs)
        self.assertTrue(ptxt.find("223") > -1)
        self.assertTrue(ptxt.find("{1}") > -1)
        self.assertTrue(ptxt.find("{3}") > -1)
        self.assertTrue(ptxt.find("{4}") == -1)
    def test_getComponent(self):
        x = LocData("/foo/bar/", testing=True)
        self.assertEquals("baz", x.getComponent("baz"))
        self.assertEquals("baz", x.getComponent("baz/a/b/c.js"))
        if os.name == 'nt':
            self.assertEquals("baz", x.getComponent(r"baz\a\b\c.js"))
        self.assertEquals("baz", x.getComponent("baz/"))
    def test_getNamingPat(self):
        x = LocData("/foo/bar/", testing=True)
        self.assertEquals("baz/a/b/strings-%s.js", x.getNamingPat("baz/a/b/strings-fr.js"))
        self.assertEquals("baz/a/b/strings-%s.js", x.getNamingPat("baz/a/b/strings-zh_TW.js"))
        self.assertEquals("baz/a/b/FOOstrings-%s.js", x.getNamingPat("baz/a/b/FOOstrings-en.js"))
        self.assertEquals("baz/a/b/x-strings-%s.js", x.getNamingPat("baz/a/b/x-strings-zh_CN.js"))
        self.assertEquals("baz/a/b/x-strings-%s.js.json", x.getNamingPat("baz/a/b/x-strings-zh_CN.js.json"))
    def test_CHECK_BRACKET_PAIRS(self):
        m = GETTEXT_PAT.finditer("_('Built on {0}', [this.packageRecord.data.runDate.format('m/d/Y') ])")
        for x in m:
            self.assertFalse(matchPairs(x.group(3)))
        self.assertEqual(matchPairs("{[(]})"), ['No closing for (.', 'No opening for ).'])
    def test_CHECK_ORPHANED_BACKSLASHES(self):
        probs = CHECK_ORPHANED_BACKSLASHES.check("This is a string \with no reason for an embedded backslash", None)
        self.assertTrue(probs)
        self.assertTrue(probs.find('backslash') > -1)
    def test_CHECK_EG(self):
        probs = ABBREVIATION_PAT.findall("This is an e.g eg e.g. eg.")
        self.assertTrue(probs)
        self.assertEquals(probs, ['e.g', 'eg', 'e.g.', 'eg.'])
    def test_CHECK_COMMON_TYPOS(self):
        self.assertFalse(COMMON_TYPOS_PAT.findall('sadness gatehouse headnote statehood'))
        self.assertTrue(COMMON_TYPOS_PAT.findall("Teh eggs adn ham."))
    def test_CHECK_AND_OR_BUT(self):
        probs = AND_OR_BUT_PAT.findall('But he came back and left again.')
        self.assertTrue(probs)
        self.assertFalse(probs.count('and') > 0)
        probs = AND_OR_BUT_PAT.findall('He came back and left again.')
        self.assertFalse(probs)
    def test_CHECK_CAN_NOT(self):
        self.assertTrue(CAN_NOT_PAT.findall("I can nOt find my keys."))
    def test_CHECK_CONTRACTIONS(self):
        probs = re.finditer(r"([A-Za-z0-9-]+)\'(t|ll)", "I can't find my keys and my mom couldn't help me. I'll have to find them on my own.")
        self.assertTrue(probs)
        for match in probs:
            self.assertTrue(match.group(0).find("'t") > -1 or match.group(0).find("'ll") > -1)
    def test_CHECK_DIR(self):
        probs = DIR_PAT.findall("That dir is in a dirty directory")
        self.assertTrue(len(probs) == 2)
    def test_CHECK_FNAME(self):
        self.assertTrue(FNAME_PAT.findall('The filename is the same as the fname.'))
    def test_CHECK_INTERNET(self):
        self.assertTrue(re.findall(r"internet","The internet is great!"))
    def test_CHECK_EMAIL(self):
        self.assertTrue(re.findall(r"e-mail","I'll e-mail you the file."))
    def test_CHECK_SPACES(self):
        self.assertTrue(re.findall(r"\s(\,|\.|\?|\;|\:)","Invalid , punctuation ; : ? . This is a proper one."))
    def test_CHECK_COMMA(self):
        probs = re.findall(r",\s?([A-Za-z0-9-]+)\s?and",r"Grapes, Apples, and Oranges. Red, Blue and Green")
        self.assertTrue(probs)
        self.assertTrue(len(probs) == 1)
        self.assertTrue(probs.count("Apples") == 0)
    def test_CHECK_SEMI_COMLON(self):
        self.assertTrue(re.finditer(r",(\s?)(?=[however])",r"The file was marked for deletion, however it may still exist on disk."))
    def test_CHECK_ALOT(self):
        self.assertTrue(re.findall(r"\s?(alot|Alot)\s", "You say alot Alot."))
    def test_CHECK_CPU_RAM(self):
        self.assertTrue(re.finditer(r"cpus?|ram|((dv)|(c))ds?|usb",r"The amount of ram you have is too low to work with your cpu. Your cd tray does not accept dvds"))
    def test_CHECK_SHOULD_OF(self):
        self.assertTrue(SHOULD_OF_PAT.findall("He should of left the dog alone; if he would of he could of been fine. He must of been stupid."))
        self.assertFalse(SHOULD_OF_PAT.findall("It is a mould of clay."))
    def test_CHECK_TTY(self):
        self.assertTrue(re.findall(r"(\*|\_)[A-Za-z0-9-]+(\*|\_)",r"This should *not* be an _issue_."))
    def test_CHECK_BACKWARDS(self):
        self.assertTrue(re.finditer(r"((any|some)\s(where|more))|(back|for)\s?wards",r"any where some where forwards backwards"))
    def test_CHECK_DEPRICATED(self):
        self.assertTrue(re.finditer(r"depreciate(d?)",r"The code is depreciated."))
    def test_CHECK_SHORTEN(self):
        self.assertTrue(re.findall(r"((((d|D)ue)\stoo?)|(in\sspite\sof))(\sthe\sfact(\sthat)?)",r"Due to the fact, in spite of the fact that."))
    def test_CHECK_REGARDING(self):
        self.assertTrue(re.findall(r"((r|R)(e|E))+?(\.|\:)?(re|RE)?",r"Re: re re. rere RE:re"))
    def test_CHECK_ETC(self):
        self.assertTrue(re.findall(r"(e|E)tc(\.?)+",r"Etc.. etc etc."))
    def test_CHECK_PERCENT(self):
        self.assertTrue(re.findall(r"(p|P)er\scent",r"100 per cent"))
    def test_CHECK_CTRL_ALT_F(self):
        self.assertFalse(CHECK_CTRL_ALT_F.check("CTRL+ALT+F7", None))
        self.assertTrue(CHECK_CTRL_ALT_F.check("CTRL + ALT + F7", None))
        self.assertTrue(CHECK_CTRL_ALT_F.check("ALT+CTRL+I", None))
        self.assertFalse(CHECK_CTRL_ALT_F.check("CTRL+ALT+Y", None))
    def test_CHECK_SIZE_ABBREVIATION(self):
        probs = re.findall(r"\b[MGKT]b|\b[mgkt][bB]|[a-z][bB]ytes|\b[kKmMgGtT]i[Bb]","Mb meg MiB mbytes")
        self.assertTrue(probs)
        self.assertEqual(3, len(probs))
    def test_CHECK_MHZ(self):
        self.assertTrue(re.finditer(r"[mgkt][hH][zZ]|[mgktMGKT]h[zZ]","Mhz mhz GHz ghz mHz"))
    def test_CHECK_ELLIPSIS(self):
        self.assertTrue(re.findall(r"\[\.*\]","Some te[...]"))
    def test_CHECK_BANDWIDTH_ABBREVIATION(self):
        self.assertTrue(CHECK_BANDWIDTH_ABBREVIATION.check("TbPs", None))
        self.assertFalse(CHECK_BANDWIDTH_ABBREVIATION.check("Mbps", None))
    def test_CHECK_CURLY_QUOTES(self):
        s = "%s%s%s%s" % (chr(145), chr(146), chr(147), chr(148))
        self.assertTrue(FIND_CURLY_QUOTE_PAT.finditer(s))
    def test_FIND_SINGLE_PAT(self):
        self.assertTrue(FIND_SINGLE_PAT.findall('''layout: 'border',
          items: [{
              xtype: 'panel',
              margins: '10 10 10 10',
              region: 'center',
              layout: 'fit','''))
        self.assertTrue(FIND_SINGLE_PAT.findall('''title: _('Manage'),'''))
        self.assertTrue(FIND_SINGLE_PAT.findall('''\'folderexists': function (me, node, rec) {
            Ext.Msg.alert('The "' + node.attributes.name + '" folder is already chosen.');
            },
            'parentfolderexists': function (me, node, rec) {
            Ext.Msg.alert('The parent folder for ' + node.attributes.name + ' is already chosen.');'''))
    def test_FORMAT_SPECIFIERS_PAT(self):
        probs = FORMAT_SPECIFIERS_PAT.findall("'folderexists': function (me, node, rec) {")
        self.assertFalse(probs)
        probs = FORMAT_SPECIFIERS_PAT.finditer('''Ext.Msg.alert('The "' + node.attributes.name + '" folder is already chosen.');''')
        self.assertTrue(probs)
        probs = FORMAT_SPECIFIERS_PAT.finditer('''\'parentfolderexists': function (me, node, rec) {
Ext.Msg.alert('The parent folder for ' + node.attributes.name + ' is already chosen.');''')
        self.assertTrue(probs)
    def test_COMMENT_PAT(self):
        self.assertTrue(COMMENT_PAT.findall('''                // Ext.get('loading').remove();
'''))
    def test_FIND_DOUBLE_PAT(self):
        self.assertTrue(FIND_DOUBLE_PAT.findall('''Ext.Msg.alert('The "' + node.attributes.name + '" folder is already chosen.');'''))
    def test_FIND_VAR(self):
        FIND_VAR_PAT = re.compile(r'var [\w]+ \=\s?')
        self.assertTrue(FIND_VAR_PAT.finditer('''var generalTplText = '<div class="general-text">{0}</div>\''''))
    def test_pureHTML(self):
        self.assertTrue(pureHTML('<div class="{iconCls}" style="width:30px; height: 30px; margin-right: 5px;"></div>'))
        self.assertFalse(pureHTML('<table style="height:100%; vertical-align: middle;"><tr><td>not html</td><td class="big-title">{title}</td></tr></table>'))
        self.assertFalse(pureHTML('<div class="{iconCls}" style="width:30px; height: 30px; margin-right: 5px;" alt="False"></div>'))
    def test_findMisses(self):
        self.assertFalse(findMisses('''      var items = [].concat(config.buttons);
      for (var i = 0; i < items.length; ++i) {
        Ext.apply(items[i], {
          xtype: 'button',
            height: 30
            });
            }
'''))
        probs = findMisses('''                  generalInfo: '<h1>Select a Destination</h1>',
                  form: {
                    xtype: 'destinationselectorpanel'
        }''')
        self.assertTrue(probs)
        self.assertTrue(len(probs) == 1)

if __name__ == '__main__':
    unittest.main()
