#!/usr/bin/env python
# encoding: utf-8

import re

from PySnipEmu.Buffer import TextBuffer
from PySnipEmu.Geometry import Span, Position

__all__ = [ "Mirror", "Transformation", "SnippetInstance", "StartMarker" ]

from PySnipEmu.debug import debug

ENDING_TAB = 0

###########################################################################
#                              Helper class                               #
###########################################################################
class _CleverReplace(object):
    """
    This class mimics TextMates replace syntax
    """
    _DOLLAR = re.compile(r"\$(\d+)", re.DOTALL)
    _SIMPLE_CASEFOLDINGS = re.compile(r"\\([ul].)", re.DOTALL)
    _LONG_CASEFOLDINGS = re.compile(r"\\([UL].*?)\\E", re.DOTALL)
    _CONDITIONAL = re.compile(r"\(\?(\d+):(.*?)(?<!\\)\)", re.DOTALL)

    _UNESCAPE = re.compile(r'\\[^ntrab]')

    def __init__(self, s):
        self._s = s

    def _scase_folding(self, m):
        if m.group(1)[0] == 'u':
            return m.group(1)[-1].upper()
        else:
            return m.group(1)[-1].lower()
    def _lcase_folding(self, m):
        if m.group(1)[0] == 'U':
            return m.group(1)[1:].upper()
        else:
            return m.group(1)[1:].lower()

    def _unescape(self, v):
        return self._UNESCAPE.subn(lambda m: m.group(0)[-1], v)[0]
    def replace(self, match):
        start, end = match.span()

        tv = self._s

        # Replace all $? with capture groups
        tv = self._DOLLAR.subn(lambda m: match.group(int(m.group(1))), tv)[0]

        def _conditional(m):
            args = m.group(2).split(':')
            # TODO: the returned string should be checked for conditionals
            if match.group(int(m.group(1))):
                return self._unescape(args[0])
            elif len(args) > 1:
                return self._unescape(args[1])
            else:
                return ""

        # Replace CaseFoldings
        tv = self._SIMPLE_CASEFOLDINGS.subn(self._scase_folding, tv)[0]
        tv = self._LONG_CASEFOLDINGS.subn(self._lcase_folding, tv)[0]
        tv = self._CONDITIONAL.subn(_conditional, tv)[0]

        rv = tv.decode("string-escape")

        return rv

###########################################################################
#                             Public classes                              #
###########################################################################
class TOParser(object):
    # A simple tabstop with default value
    _TABSTOP = re.compile(r'''\${(\d+)[:}]''')
    # A mirror or a tabstop without default value.
    _MIRROR_OR_TS = re.compile(r'\$(\d+)')
    # A mirror or a tabstop without default value.
    _TRANSFORMATION = re.compile(r'\${(\d+)/(.*?)/(.*?)/([a-zA-z]*)}')


    def __init__(self, parent, val):
        self._v = val
        self._p = parent

        self._childs = []


    def __repr__(self):
        return "TOParser(%s)" % self._p

    def parse_tabs(self):
        ts = []
        m = self._TABSTOP.search(self._v)
        while m:
            ts.append(self._handle_tabstop(m))
            m = self._TABSTOP.search(self._v)


        for t, def_text in ts:
            child_parser = TOParser(t, def_text)
            child_parser.parse_tabs()
            self._childs.append(child_parser)

    def parse_transformations(self):
        self._trans = []
        for m in self._TRANSFORMATION.finditer(self._v):
            self._trans.append(self._handle_transformation(m))

        for t in self._childs:
            t.parse_transformations()

    def parse_mirrors_or_ts(self):
        for m in self._MIRROR_OR_TS.finditer(self._v):
            self._handle_ts_or_mirror(m)

        for t in self._childs:
            t.parse_mirrors_or_ts()

    def finish(self):
        for c in self._childs:
            c.finish()

        for t in self._trans:
            ts = self._p._get_tabstop(self._p,t._ts)
            if ts is None:
                raise RuntimeError, "Tabstop %i is not known" % t._ts
            t._ts = ts


    def _handle_tabstop(self, m):
        def _find_closingbracket(v,start_pos):
            bracks_open = 1
            for idx, c in enumerate(v[start_pos:]):
                if c == '{':
                    if v[idx+start_pos-1] != '\\':
                        bracks_open += 1
                elif c == '}':
                    if v[idx+start_pos-1] != '\\':
                        bracks_open -= 1
                    if not bracks_open:
                        return start_pos+idx+1

        start_pos = m.start()
        end_pos = _find_closingbracket(self._v, start_pos+2)

        def_text = self._v[m.end():end_pos-1]

        start, end = self._get_start_end(self._v,start_pos,end_pos)

        ts = TabStop(self._p, start, end, def_text)

        self._p._add_tabstop(int(m.group(1)),ts)

        self._v = self._v[:start_pos] + (end_pos-start_pos)*" " + \
                self._v[end_pos:]

        return ts, def_text

    def _handle_ts_or_mirror(self, m):
        no = int(m.group(1))

        start_pos, end_pos = m.span()
        start, end = self._get_start_end(self._v,start_pos,end_pos)

        ts = self._p._get_tabstop(self._p, no)
        if ts is not None:
            rv = Mirror(self._p, ts, start, end)
        else:
            rv = TabStop(self._p, start, end)
            self._p._add_tabstop(no,rv)

        # Replace the whole definition with spaces
        s, e = m.span()
        self._v = self._v[:s] + (e-s)*" " + self._v[e:]

        return rv

    def _handle_transformation(self, m):
        no = int(m.group(1))
        search = m.group(2)
        replace = m.group(3)
        options = m.group(4)

        start_pos, end_pos = m.span()
        start, end = self._get_start_end(self._v,start_pos,end_pos)

        # Replace the whole definition with spaces
        s, e = m.span()
        self._v = self._v[:s] + (e-s)*" " + self._v[e:]

        return Transformation(self._p, no, start, end, search, replace, options)

    def _get_start_end(self, val, start_pos, end_pos):
        def _get_pos(s, pos):
            line_idx = s[:pos].count('\n')
            line_start = s[:pos].rfind('\n') + 1
            start_in_line = pos - line_start
            return Position(line_idx, start_in_line)

        return _get_pos(val, start_pos), _get_pos(val, end_pos)




class TextObject(object):
    """
    This base class represents any object in the text
    that has a span in any ways
    """
    def __init__(self, parent, start, end, initial_text):
        self._start = start
        self._end = end

        self._parent = parent

        self._children = []
        self._tabstops = {}

        if parent is not None:
            parent._add_child(self)

        self._current_text = TextBuffer(initial_text)

        self._cts = 0

    def __cmp__(self, other):
        return cmp(self._start, other._start)


    ##############
    # PROPERTIES #
    ##############
    def current_text():
        def fget(self):
            return str(self._current_text)
        def fset(self, text):
            self._current_text = TextBuffer(text)

            # All our children are set to "" so they
            # do no longer disturb anything that mirrors it
            for c in self._children:
                c.current_text = ""
            self._children = []
            self._tabstops = {}
        return locals()

    current_text = property(**current_text())
    def abs_start(self):
        if self._parent:
            ps = self._parent.abs_start
            if self._start.line == 0:
                return ps + self._start
            else:
                return Position(ps.line + self._start.line, self._start.col)
        return self._start
    abs_start = property(abs_start)

    def abs_end(self):
        if self._parent:
            ps = self._parent.abs_start
            if self._end.line == 0:
                return ps + self._end
            else:
                return Position(ps.line + self._end.line, self._end.col)

        return self._end
    abs_end = property(abs_end)

    def span(self):
        return Span(self._start, self._end)
    span = property(span)

    def start(self):
        return self._start
    start = property(start)

    def end(self):
        return self._end
    end = property(end)

    def abs_span(self):
        return Span(self.abs_start, self.abs_end)
    abs_span = property(abs_span)

    ####################
    # Public functions #
    ####################
    def update(self):
        for idx,c in enumerate(self._children):
            oldend = Position(c.end.line, c.end.col)

            new_end = c.update()

            moved_lines = new_end.line - oldend.line
            moved_cols = new_end.col - oldend.col

            self._current_text.replace_text(c.start, oldend, c._current_text)

            self._move_textobjects_behind(c.start, oldend, moved_lines,
                        moved_cols, idx)

        self._do_update()

        new_end = self._current_text.calc_end(self._start)

        self._end = new_end

        return new_end

    def _get_next_tab(self, no):
        if not len(self._tabstops.keys()):
            return
        tno_max = max(self._tabstops.keys())

        posible_sol = []
        i = no + 1
        while i <= tno_max:
            if i in self._tabstops:
                posible_sol.append( (i, self._tabstops[i]) )
                break
            i += 1

        c = [ c._get_next_tab(no) for c in self._children ]
        c = filter(lambda i: i, c)

        posible_sol += c

        debug("posi: %s" % (posible_sol,))
        if not len(posible_sol):
            return None

        return min(posible_sol)


    def _get_prev_tab(self, no):
        if not len(self._tabstops.keys()):
            return
        tno_min = min(self._tabstops.keys())

        posible_sol = []
        i = no - 1
        while i >= tno_min and i > 0:
            if i in self._tabstops:
                posible_sol.append( (i, self._tabstops[i]) )
                break
            i -= 1

        c = [ c._get_prev_tab(no) for c in self._children ]
        c = filter(lambda i: i, c)

        posible_sol += c

        if not len(posible_sol):
            return None

        return max(posible_sol)


    ###############################
    # Private/Protected functions #
    ###############################
    def _do_update(self):
        pass

    def _move_textobjects_behind(self, start, end, lines, cols, obj_idx):
        if lines == 0 and cols == 0:
            return

        for idx,m in enumerate(self._children[obj_idx+1:]):
            delta_lines = 0
            delta_cols_begin = 0
            delta_cols_end = 0

            if m.start.line > end.line:
                delta_lines = lines
            elif m.start.line == end.line:
                if m.start.col >= end.col:
                    if lines:
                        delta_lines = lines
                    delta_cols_begin = cols
                    if m.start.line == m.end.line:
                        delta_cols_end = cols
            m.start.line += delta_lines
            m.end.line += delta_lines
            m.start.col += delta_cols_begin
            m.end.col += delta_cols_end

    def _get_tabstop(self, requester, no):
        if no in self._tabstops:
            return self._tabstops[no]
        for c in self._children:
            if c == requester:
                continue

            rv = c._get_tabstop(self, no)
            if rv is not None:
                return rv

        if self._parent and requester != self._parent:
            return self._parent._get_tabstop(self, no)

    def _add_child(self,c):
        self._children.append(c)
        self._children.sort()

    def _add_tabstop(self, no, ts):
        self._tabstops[no] = ts



class StartMarker(TextObject):
    """
    This class only remembers it's starting position. It is used to
    transform relative values into absolute position values in the vim
    buffer
    """
    def __init__(self, start):
        end = Position(start.line, start.col)
        TextObject.__init__(self, None, start, end, "")


class Mirror(TextObject):
    """
    A Mirror object mirrors a TabStop that is, text is repeated here
    """
    def __init__(self, parent, ts, start, end):
        TextObject.__init__(self, parent, start, end, "")

        self._ts = ts

    def _do_update(self):
        self.current_text = self._ts.current_text

    def __repr__(self):
        return "Mirror(%s -> %s)" % (self._start, self._end)


class Transformation(Mirror):
    def __init__(self, parent, ts, start, end, s, r, options):
        Mirror.__init__(self, parent, ts, start, end)

        flags = 0
        self._match_this_many = 1
        if options:
            if "g" in options:
                self._match_this_many = 0
            if "i" in options:
                flags |=  re.IGNORECASE

        self._find = re.compile(s, flags)
        self._replace = _CleverReplace(r)

    def _do_update(self):
        t = self._ts.current_text
        t = self._find.subn(self._replace.replace, t, self._match_this_many)[0]
        self.current_text = t

    def __repr__(self):
        return "Transformation(%s -> %s)" % (self._start, self._end)


class TabStop(TextObject):
    """
    This is the most important TextObject. A TabStop is were the cursor
    comes to rest when the user taps through the Snippet.
    """
    def __init__(self, parent, start, end, default_text = ""):
        TextObject.__init__(self, parent, start, end, default_text)

    def __repr__(self):
        return "TabStop(%s -> %s, %s)" % (self._start, self._end,
            repr(self._current_text))

class SnippetInstance(TextObject):
    """
    A Snippet instance is an instance of a Snippet Definition. That is,
    when the user expands a snippet, a SnippetInstance is created to
    keep track of the corresponding TextObjects. The Snippet itself is
    also a TextObject because it has a start an end
    """

    def __init__(self, parent, initial_text):
        start = Position(0,0)
        end = Position(0,0)

        TextObject.__init__(self, parent, start, end, "")

        self._current_text = TextBuffer(self._parse(initial_text))
        self._end = self._current_text.calc_end(start)

        TextObject.update(self)

        # Check if we have a zero Tab, if not, add one at the end
        if 0 not in self._tabstops:
            delta = self._end - self._start
            col = self.end.col
            if delta.line == 0:
                col -= self.start.col
            start = Position(delta.line, col)
            end = Position(delta.line, col)
            ts = TabStop(self, start, end, "")
            self._add_tabstop(0,ts)

            TextObject.update(self)

    def __repr__(self):
        return "SnippetInstance(%s -> %s)" % (self._start, self._end)


    def _get_tabstop(self, requester, no):
        # SnippetInstances are completly self contained,
        # therefore, we do not need to ask our parent
        # for Tabstops
        # TODO: otherwise, this code is identical to
        # TextObject._get_tabstop
        if no in self._tabstops:
            return self._tabstops[no]
        for c in self._children:
            if c == requester:
                continue

            rv = c._get_tabstop(self, no)
            if rv is not None:
                return rv

    def _parse(self, val):
        if not len(val):
            return val

        to = TOParser(self, val)
        to.parse_tabs()
        to.parse_transformations()
        to.parse_mirrors_or_ts()
        to.finish()

        return val


    def select_next_tab(self, backwards = False):
        if backwards:
            cts_bf = self._cts

            res = self._get_prev_tab(self._cts)
            if res is None:
                self._cts = cts_bf
                return self._tabstops[self._cts]
            self._cts, ts = res
            return ts
        else:
            res = self._get_next_tab(self._cts)
            if res is None:
                self._cts = 0
                if 0 not in self._tabstops:
                    return None
            else:
                self._cts, ts = res
                return ts

        return self._tabstops[self._cts]

