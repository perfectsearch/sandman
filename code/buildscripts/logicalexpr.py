# 
# $Id: filename 3521 2010-11-25 00:31:22Z svn_username $
# 
# Proprietary and confidential.
# Copyright $Date:: 2010#$ Perfect Search Corporation.
# All rights reserved.
# 
import re

class ParseError(Exception):
    def __init__(self, msg):
        self.message = msg
    def __str__(self):
        return self.message

class ParseNode:
    def __init__(self, kind, value, head):
        self.kind = kind
        self.value = value
        self.prev = None
        if head:
            self.prev = head.getLast()
            self.prev.next = self
        self.next = None
        self.child = None
    def getFirst(self):
        if self.prev:
            return self.prev.getFirst()
        return self
    def getLast(self):
        if self.next:
            return self.next.getLast()
        return self
    def getIndex(self):
        i = -1
        x = self
        while x:
            i += 1
            x = x.prev
        return i
    def __str__(self):
        if self.kind == 'group':
            txt = ('(' + str(self.child) + ')')
        elif self.kind == 'expr':
            txt = str(self.child)
        else:
            txt = self.value
        if self.next:
            return txt + ' ' + str(self.next)
        else:
            return txt

class Value:
    def __init__(self, root):
        self.root = root
    def __call__(self, scanner, token):
        #print('in value; token=%s' % token)
        node = ParseNode('value', token, self.root.head)
        if not self.root.head:
            self.root.head = node
        return node

class Operator:
    def __init__(self, root):
        self.root = root
    def __call__(self, scanner, token):
        #print('in operator; token=%s' % token)
        node = ParseNode('operator', token.upper(), self.root.head)
        if not self.root.head:
            self.root.head = node
        return node

class Nest:
    def __init__(self, root):
        self.root = root
    def __call__(self, scanner, token):
        #print('in nest; token=%s' % token)
        node = ParseNode('nest', token, self.root.head)
        if not self.root.head:
            self.root.head = node
        return node
    
def bind(parseTree):
    parseTree = bind_groups(parseTree)
    print('before bind_unary ' + str(parseTree))
    parseTree = bind_unary(parseTree, 'NOT')
    print('before bind_binary AND ' + str(parseTree))
    parseTree = bind_binary(parseTree, 'AND')
    print('after bind_binary AND' + str(parseTree))
    parseTree = bind_binary(parseTree, 'OR')
    return parseTree

def bind_unary(parseTree, op):
    node = parseTree
    while node:
        if (node.kind == 'operator') and (node.value == op):
            if node.next:
                if node.next.kind != 'operator':
                    expr = chop_tokens(node, node.next, 'expr')
                    expr.child = node
                    # If we just turned the first two nodes in the
                    # parsetree into an expr, then change what our head
                    # node points to.
                    if not expr.prev:
                        parseTree = expr
                        print('modified parseTree; new val = ' + str(parseTree))
                    node = expr
                else:
                    raise ParseError('%s cannot be followed by operator' % op)
            else:
                raise ParseError('%s missing an operand' % op)
        node = node.next
    return parseTree
                
def bind_binary(parseTree, op):
    node = parseTree
    while node:
        if (node.kind == 'operator') and (node.value == op):
            if node.next:
                if node.next.kind != 'operator':
                    if node.prev:
                        if node.prev.kind != 'operator':
                            expr = chop_tokens(node.prev, node.next, 'expr')
                            expr.child = node.prev
                            # If we just turned the first three nodes in the
                            # parsetree into an expr, then change what our head
                            # node points to.
                            if not expr.prev:
                                #print('resetting parseTree')
                                parseTree = expr
                            node = expr
                        else:
                            raise ParseError('%s cannot be preceded by operator' % op)
                    else:
                        raise ParseError('%s should be preceded by an operand' % op)
                else:
                    raise ParseError('%s cannot be followed by operator' % op)
            else:
                raise ParseError('%s should be followed by an operand' % op)
        node = node.next
    print('at end of bind_binary; parseTree = ' + str(parseTree))
    return parseTree

def chop_tokens(begin, end, newKind):
    bidx = begin.getIndex()
    eidx = end.getIndex()
    oldlen = begin.getLast().getIndex() + 1
    expr = ParseNode(newKind, None, None)
    expr.prev = begin.prev
    if begin.prev:
        begin.prev.next = expr
    print('hooking up new expr to ' + str(end.next))
    expr.next = end.next
    if end.next:
        end.next.prev = expr
    begin.prev = None
    end.next = None
    print('chopped from %s%d to %s%d; old len = %d, new = %d' % 
          (begin.value, bidx, end.value, eidx, oldlen, expr.getLast().getIndex() + 1))
    return expr

def bind_groups(parseTree):
    print('binding groups on ' + str(parseTree))
    nest = 0
    node = parseTree
    begin = end = None
    while node:
        if node.kind == 'nest':
            if node.value == '(':
                nest += 1
                if nest == 1:
                    begin = node
            else:
                if nest == 1:
                    end = node
                    # Turn flat, linear list into tree -- treat group as
                    # an independent list of its own, a child of a new
                    # node of type 'group'.
                    grp = chop_tokens(begin, end, 'group')
                    # If our first node is now a group instead of a paren,
                    # then change what our head node points to.
                    if not grp.prev:
                        parseTree = grp
                    # The call to chop_tokens will have already dissociated this
                    # grouped, linked list of nodes from the larger context.
                    # Now we want to remove the paren tokens as well.
                    begin.next.prev = None
                    end.prev.next = None
                    # Now recurse on child list, and link into overall tree.
                    print('recursing')
                    grp.child = bind(begin.next)
                    node = grp
                    begin = end = None
                nest -= 1
                if nest < 0:
                    raise ParseError('Extra )')
        node = node.next
    if nest != 0:
        raise ParseError('Unmatched (')
    return parseTree

class ParseRoot:
    def __init__(self):
        self.head = None
root = ParseRoot()

if False:
    scanner = re.Scanner([
        (r"(a(?!nd\s)|o(?!r\s)|n(?!ot\s)|[^aon() ])[^() ]*", Value(root)),
        (r'and|or|not', Operator(root)),
        (r'[()]', Nest(root)),
        (r"\s+", None),
        ])
     
    tokens, remainder = scanner.scan(
        #"a and (b or not (c AND d))"
        "e not c or (a and not d)"
    )
    if remainder:
        raise ParseError('Unparseable data at "%s"' % remainder)
    
    for token in tokens:
        print('%d %s' % (token.getIndex(), token.value))
        
    parseTree = bind(root.head)
    print(parseTree)

