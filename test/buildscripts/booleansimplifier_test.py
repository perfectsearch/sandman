#!/usr/bin/env python
import unittest, booleansimplifier
from testsupport import checkin

@checkin
class BooleanSimplifierTest(unittest.TestCase):
    def __init__(self, methodName = 'runTest'):
        unittest.TestCase.__init__(self, methodName)
        longMessage = True
    def test_and_substitution(self):
        # The only normal case
        input = (' and ')
        result = booleansimplifier.replace_operations(input)
        self.assertTrue(result and '&' in result,
                        'Failed with argument "%s", result "%s"' % (input, result))
        failureInputs = ('and b', 'a and', 'aand ', ' andb')
        for input in failureInputs:
            result = booleansimplifier.replace_operations(input)
            self.assertFalse(result and '&' in result,
                            'Failed with argument "%s", result "%s"' % (input, result))
        self.assertEqual('checkin & ! interactive', booleansimplifier.replace_operations('checkin and not interactive'))
    def test_or_substitution(self):
        # The only normal case
        input = ('a or b')
        result = booleansimplifier.replace_operations(input)
        self.assertTrue(result and '|' in result,
                        'Failed with argument "%s", result "%s"' % (input, result))
        failureInputs = ('or b', 'a or', 'aor ', ' orb')
        for input in failureInputs:
            result = booleansimplifier.replace_operations(input)
            self.assertFalse(result and '|' in result,
                            'Failed with argument "%s", result "%s"' % (input, result))
    def test_not_substitution(self):
        # The only normal case
        successInputs = (' not ', 'not ')
        for input in successInputs:
            result = booleansimplifier.replace_operations(input)
            self.assertTrue(result and '!' in result,
                            'Failed with argument "%s", result "%s"' %
                            (input, result))
        failureInputs = ('notb', 'inot')
        for input in failureInputs:
            result = booleansimplifier.replace_operations(input)
            self.assertFalse(result and '!' in result,
                            'Failed with argument "%s", result "%s"' %
                            (input, result))
    def test_strip(self):
        result = booleansimplifier.strip(' a) (b! ! ')
        self.assertFalse(' ' in result, 'Actual result is "%s" - should not contain any space character' % result)
        self.assertFalse('!!' in result, 'Actual result is "%s" - should not contain "!!" substrings' % result)
        self.assertRaises(booleansimplifier.ValidateBooleanException, booleansimplifier.strip, ('a b'))
    def test_validate(self):
        successInputs = ('((', '(!', '(q', '))', ')|', ')&', '|(', '|!', '|q', '&(', '&!', '&q', '!(', '!q', 'q)', 'q|', 'q&')
        for input in successInputs:
            try:
                booleansimplifier.validate('((!(a))|(')
            except booleansimplifier.ValidateBooleanException as e:
                self.assertTrue(False, 'Failed to validate valid string "%s"' % input)
        failureInputs = ('()', '(|', '(&', ')(', ')!', ')q', '|)', '||', '|&', '&)', '&|', '&&', '!)', '!|', '!&', '!!', 'q(', 'q!', '+')
        for input in failureInputs:
            self.assertRaises(booleansimplifier.ValidateBooleanException, booleansimplifier.validate, (input))
    def test_check_parens_balanced(self):
        booleansimplifier.check_parens_balanced('((())())')
        failureInputs = ('(()', '())')
        for input in failureInputs:
            self.assertRaises(booleansimplifier.ValidateBooleanException, booleansimplifier.check_parens_balanced, (input))
    def test_split_on_conjunction(self):
        self.assertEqual(list(('!(a&b)', 'c')), booleansimplifier.split_on_conjunction('!(a&b)|c'))
        self.assertEqual(list(('!(a|b)', 'c')), booleansimplifier.split_on_conjunction('!(a|b)|c'))
        # Making a list from a single string
        supposed = list()
        supposed.append('!(a|b)')
        self.assertEqual(supposed, booleansimplifier.split_on_conjunction('!(a|b)'))
    def test_split_disjunctive(self):
        self.assertEqual(list(('!(a&b)', 'c')), booleansimplifier.split_disjunctive('!(a&b)&c'))
        self.assertEqual(list(('(a&b)', 'c')), booleansimplifier.split_disjunctive('(a&b)&c'))
        self.assertEqual(list(('!(a&b)', 'c', '!(d|e)')), booleansimplifier.split_disjunctive('!(a&b)&c&!(d|e)'))
        # Making a list from a single string
        supposed = list()
        supposed.append('!(a|b)')
        self.assertEqual(supposed, booleansimplifier.split_on_conjunction('!(a|b)'))
    def test_cmp_terms(self):
        self.assertEqual(0, booleansimplifier.cmp_terms('(', '('))
        self.assertEqual(0, booleansimplifier.cmp_terms('r', 'q'))
        self.assertEqual(-1, booleansimplifier.cmp_terms('r', '('))
        self.assertEqual(1, booleansimplifier.cmp_terms('(', 'q'))
        self.assertEqual(list(('a', 'c', 'e', '(b)', '(d)')), sorted(list(('a', '(b)', 'c', '(d)', 'e')), booleansimplifier.cmp_terms))
    def test_separate_parenthesized(self):
        flat, parenthesied = booleansimplifier.separate_parenthesized(list(('a', '(b)', 'c', '(d)', 'e')))
        self.assertEqual(flat, "a&c&e")
        self.assertEqual(parenthesied, list(('(b)', '(d)')))
        flat, parenthesied = booleansimplifier.separate_parenthesized(list(('(b)', '(d)')))
        self.assertTrue(flat is None)
        self.assertEqual(parenthesied, list(('(b)', '(d)')))
        flat, parenthesied = booleansimplifier.separate_parenthesized(list(('a', 'c', 'e')))
        self.assertEqual(flat, "a&c&e")
        self.assertEqual(parenthesied, list())
    def test_negate(self):
        self.assertEqual('a&!(b|c)|!d', booleansimplifier.negate('!a|(b|c)&d'))
    def test_open_parens(self):
        self.assertEqual('a&!(b|c)|!d', booleansimplifier.open_parens('!(!a|(b|c)&d)'))
        self.assertEqual('a|(b|c)&d', booleansimplifier.open_parens('(a|(b|c)&d)'))
    def test_and_monomial(self):
        self.assertEqual(['b', 'c'], booleansimplifier.and_monomial(None, ['b', 'c']))
        self.assertEqual(['a'], booleansimplifier.and_monomial('a', list()))
        self.assertEqual(['a&b', 'a&c'], booleansimplifier.and_monomial('a', ['b', 'c']))
    def test_and_polynomial(self):
        self.assertEqual(['c', 'd'], booleansimplifier.and_polynomial(list(), ['c', 'd']))
        self.assertEqual(['a', 'b'], booleansimplifier.and_polynomial(['a', 'b'], list()))
        self.assertEqual(['a&c', 'a&d', 'b&c', 'b&d'], booleansimplifier.and_polynomial(['a', 'b'], ['c', 'd']))
    def test_process_disjunctive(self):
        self.assertEqual(['a&c&b&d', 'a&c&b&e'], booleansimplifier.process_disjunctive('a&(b)&c&(d|e)'))
    def test_process_expression(self):
        self.assertEqual('a&c&b&d|a&c&b&e|f&g', booleansimplifier.process_expression('a and (b) and c and (d or e) or f and g'))
        self.assertEqual('checkin&!interactive', booleansimplifier.process_expression('checkin and not interactive'))
