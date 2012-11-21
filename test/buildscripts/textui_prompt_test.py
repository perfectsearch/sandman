#
# $Id: build_ansi.py 9736 2011-06-20 16:49:22Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import unittest, os, sys, StringIO
from textui.prompt import *
from nose.tools import istest, nottest
from nose.plugins.attrib import attr

_explained = False

def _text_repeats(txt, fragment):
    i = txt.find(fragment)
    if i > -1:
        i = txt[i + len(fragment):].find(fragment)
        return i > -1
    return False

def _text_has(txt, fragment):
    return txt.find(fragment) > -1

@attr('interactive')
class InteractivePromptTest(unittest.TestCase):
    def stuff(self, txt_for_stdin):
        # Overridden in AutomatedPromptTest
        pass
    def assertStdout(self, expectFunc, arg):
        # Overridden in AutomatedPromptTest
        return True
    def explain(self, txt):
        global _explained
        if not _explained:
            print('''
INTERACTIVE TEST -- PLEASE FOLLOW INSTRUCTIONS

This test checks our ability to user input correctly. It depends on you typing
some simple responses. It is not particularly sensitive to typos, but you
should NOT just press Enter to get through the test, or you may see spurious
failures.
''')
            _explained = True
        else:
            print('')
        print(txt.strip() + '\n')
    def test_prompt(self):
        self.explain('''
Answer the following question with at least a few chars. If the prompt()
function is working, we should see a non-empty answer.
''')
        self.stuff('to seek the holy grail\n')
        answer = prompt('What is your quest?')
        self.assertTrue(answer)
        # Answer should never include trailing \n
        self.assertEquals(answer.rstrip(), answer)
    def test_prompt_bool_word_true(self):
        self.explain('''
Answer the following question accurately with a FULL WORD, not a single char. In
other words, type "yes" or "no" as your answer. Case doesn't matter.
''')
        self.stuff('YeS\n')
        answer = prompt_bool('Does this line end with a "(y/n)" prompt?')
        self.assertTrue(isinstance(answer, bool))
        self.assertTrue(answer)
        self.assertStdout(_text_has, '? (y/n)')
    def test_prompt_bool_char_true(self):
        self.explain('''
Answer the following question with the THE "Y" CHAR, not a full word. Case
doesn't matter.
''')
        self.stuff('Y\n')
        answer = prompt_bool('Are you sure?')
        self.assertTrue(isinstance(answer, bool))
        self.assertTrue(answer)
    def test_prompt_bool_word_false(self):
        self.explain('''
Answer the following question accurately with THE WORD "NO", not a single char.
Case doesn't matter.
''')
        self.stuff('nO\n')
        answer = prompt_bool('Do chickens have lips?', False)
        self.assertTrue(isinstance(answer, bool))
        self.assertFalse(answer)
        self.assertStdout(_text_has, '? (y/N)')
    def test_prompt_bool_char_false(self):
        self.explain('''
Answer the following question accurately with THE "N" CHAR, not a full word.
Case doesn't matter.
''')
        self.stuff('n\n')
        answer = prompt_bool('Can pigs fly?')
        self.assertTrue(isinstance(answer, bool))
        self.assertFalse(answer)
    def test_prompt_bool_repeats(self):
        self.explain('''
This test checks to see whether we require a genuine boolean response from
someone instead of letting them type garbage. Answer the question ONCE WITH THE
WORD "pickle". You should get reprompted. Answer THE SECOND TIME WITH "N"/"NO".
''')
        self.stuff('pickle\nNo\n')
        answer = prompt_bool('Do frogs have fur?')
        self.assertTrue(isinstance(answer, bool))
        self.assertStdout(_text_repeats, 'have fur')
    def test_prompt_masked(self):
        self.explain('''
This test checks to see whether we can prompt for a password without displaying
what you type.
''')
        answer = prompt('Type an imaginary password:', readline=readline_masked)
        self.assertTrue(prompt_bool('Were your keystrokes masked out?'))
    def test_prompt_enter(self):
        self.stuff('\n')
        answer = prompt('\nPress Enter:', default="blue")
        self.assertEqual('blue', answer)
        self.assertStdout(_text_has, '( =blue)')
    def test_prompt_enter_again(self):
        self.stuff('\n')
        answer = prompt('\nPress Enter again:')
        self.assertEqual('', answer)
    def test_prompt_enter_require_answer(self):
        self.explain('''
This test checks to see whether we can force the user to give an answer. THE
FIRST TIME you are prompted, PRESS ENTER. The second time, give a real answer.
''')
        self.stuff('\nFred\ny\n')
        answer = prompt('What is your name?', default=None)
        self.assertTrue(prompt_bool('Were you re-prompted?'))
        self.assertStdout(_text_repeats, 'your name')

class AutomatedPromptTest(InteractivePromptTest):
    def assertStdout(self, func, arg):
        self.assertTrue(func(sys.stdout.getvalue(), arg))
    def stuff(self, txt_for_stdin):
        sys.stdin.write(txt_for_stdin)
        sys.stdin.seek(0)
    def explain(self, txt):
        pass
    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = StringIO.StringIO()
        self.stdin = sys.stdin
        sys.stdin = StringIO.StringIO()
    def tearDown(self):
        sys.stdout = self.stdout
        sys.stdin = self.stdin
    def test_prompt_masked(self):
        # getch can't be automatically overridden without side effects
        pass

if __name__ == '__main__':
    tl = unittest.TestLoader()
    if '--interactive' in sys.argv:
        suite = tl.loadTestsFromTestCase(InteractivePromptTest)
    else:
        suite = tl.loadTestsFromTestCase(AutomatedPromptTest)
    tr = unittest.TextTestRunner()
    result = tr.run(suite)
    sys.exit(int(not result.wasSuccessful()))
