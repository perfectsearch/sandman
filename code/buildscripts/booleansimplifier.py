import re, logging

log = logging.getLogger('booleansimplifier')

RE_REPLACE_AND = re.compile(r'([^\w])and([^\w])', re.I)
RE_REPLACE_OR = re.compile(r'([^\w])or([^\w])', re.I)
RE_REPLACE_FIRST_NOT = re.compile(r'^not([^\w])', re.I)
RE_REPLACE_OTHER_NOT = re.compile(r'([^w])not([^\w])', re.I)

RE_TWO_WORDS = re.compile(r'\w\s\w')
RE_INVALID_SEQUENCES = re.compile(r'\([\)|&]|\)[\(!\w]|\|[\)&|]|&[\)&|]|![\)&|!]|\w[\(!]|[^\(\)&|!\w]')

class ValidateBooleanException(Exception):
    def __init__(self, inputString, position, message):
        self.inputString = inputString
        self.position = position
        self.message = message
    def __str__(self):
        return 'Validity check failed in "%s" at position %i. Reason: %s' % (self.inputString, self.position, self.message)

def replace_operations(input):
    output = re.sub(RE_REPLACE_AND, r'\1&\2', input)
    output = re.sub(RE_REPLACE_OR, r'\1|\2', output)
    output = re.sub(RE_REPLACE_FIRST_NOT, r'!\1', output)
    return re.sub(RE_REPLACE_OTHER_NOT, r'\1!\2', output)

def strip(input):
    twm = re.match(RE_TWO_WORDS, input)
    if twm:
        raise ValidateBooleanException(input, twm.start(), "bare word detected")
    return re.sub('!!', '', re.sub(r'\s*', '', input))

def validate(input):
    twm = re.match(RE_INVALID_SEQUENCES, input)
    if twm:
        raise ValidateBooleanException(input, twm.start(), "invalid character sequence detected")

def check_parens_balanced(input):
    counter = 0
    for i in range(len(input)):
        if input[i] == '(':
            counter = counter + 1
        elif input[i] == ')':
            counter = counter - 1
            if counter < 0:
                raise ValidateBooleanException(input, i, "unmatched closing parenthesis")
    if counter > 0:
        raise ValidateBooleanException(input, -1, "unmatched open parenthesis")

def split_on_conjunction(input):
    """
    Splits an input statement into the list of disjunctive terms on the highest level present
    """
    disjuncts = list()
    start = 0
    counter = 0
    for i in range(len(input)):
        if input[i] == '(':
            counter = counter + 1
        if input[i] == ')':
            counter = counter - 1
        if input[i] == '|' and counter == 0:
            disjuncts.append(input[start:i])
            start = i + 1
    disjuncts.append(input[start:])
    return disjuncts

def split_disjunctive(input):
    disjuncts = list()
    start = 0
    counter = 0
    idxStart = 0
    if input[idxStart] == '!':
        idxStart = 1
    if input[idxStart] == '(':
        counter = 1
        idxStart = idxStart + 1
    for i in range(idxStart, len(input)):
        if input[i] == '(':
            counter = counter + 1
        elif input[i] == ')':
            counter = counter - 1
        elif input[i] == '&' and counter == 0:
            disjuncts.append(input[start:i])
            start = i + 1
    disjuncts.append(input[start:])
    return disjuncts

def cmp_terms(term1, term2):
    if not '(' in term1 and '(' in term2:
        return -1
    elif '(' in term1 and not '(' in term2:
        return 1
    return 0

def separate_parenthesized(inputList):
    """
    Traverses list of terms and returns a disjunctive term and a list of parenthesized terms
    """
    sortedInput = sorted(inputList, cmp_terms)
    flat = None
    for i in range(len(sortedInput)):
        if '(' in sortedInput[i]:
            return flat, sortedInput[i:]
        else:
            if flat:
                flat = "%s&%s" % (flat, sortedInput[i])
            else:
                flat = sortedInput[i]
    return flat, list()

def negate(input):
    counter = 0
    substitutions = { '&':'|!', '|':'&!' }
    result = "!"
    for i, ch in enumerate(input):
        if ch == '(':
            counter = counter + 1
        elif ch == ')':
            counter = counter - 1
        if ch in '&|' and counter == 0:
            result = result + substitutions[ch]
        else:
            result = result + ch
    return re.sub('!!', '', result)

def open_parens(input):
    if input[0] == '!':
        return negate(input[2:-1])
    return input[1:-1]

def and_monomial(monome, polynome):
    """
    Multiplies monome and polynome. Returns a list containing monomes (virtually or'ed).
    """
    if not monome:
        return polynome
    result = list()
    if not polynome:
        result.append(monome)
    else:
        for term in polynome:
            result.append("%s&%s" % (monome, term))
    return result

def and_polynomial(poly1, poly2):
    if not poly1:
        return poly2
    if not poly2:
        return poly1
    result = list()
    for term in poly1:
        result = result + and_monomial(term, poly2)
    return result

def process_disjunctive(input):
    """
    Opens parentheses in a given disjunctive term. Each disjunctive term in the result will be anded with a "prefixial" one.
    Returns list of terms should be connected with "or" operation.
    """
    terms, parenthesized = separate_parenthesized(split_disjunctive(input))
    result = list()
    for nextTerm in parenthesized:
        newStatement = open_parens(nextTerm)
        disjuncts = split_on_conjunction(newStatement)
        intermediate = list()
        for disjunctive in disjuncts:
            intermediate = intermediate + process_disjunctive(disjunctive)
        result = and_polynomial(result, intermediate)
    result = and_monomial(terms, result)
    return result

def process_expression(input):
    intermediate = strip(replace_operations(input))
    validate(intermediate)
    check_parens_balanced(intermediate)
    toBeOr_ed = process_disjunctive('(' + intermediate + ')')
    return '|'.join(toBeOr_ed)
