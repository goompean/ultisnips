" Syntax highlighting for snippet files (used for UltiSnips.vim)
" Revision: 26/03/11 19:53:33

if exists("b:current_syntax")
  finish
endif

" Embedded Syntaxes {{{1

syntax include @Python syntax/python.vim
unlet b:current_syntax
syntax include @Viml syntax/vim.vim
unlet b:current_syntax
syntax include @Shell syntax/sh.vim
unlet b:current_syntax

" Syntax definitions {{{1

" Comments {{{2

syn match snipComment "^#.*" contains=snipTODO display
syn keyword snipTODO contained display FIXME NOTE NOTES TODO XXX

" Miscellaneous {{{2

syn match snipDocString '"[^"]*"$'
syn match snipString '"[^"]*"'
syn match snipTabsOnly "^\t\+$"
syn match snipLeadingSpaces "^\t* \+"

syn match snipKeyword "\(\<\(end\)\?\(snippet\|global\)\>\)\|extends\|clearsnippets\|priority" contained

" Extends {{{2

syn match snipExtends "^extends\%(\s.*\|$\)" contains=snipExtendsKeyword display
syn match snipExtendsKeyword "^extends" contained display

" Definitions {{{2

" snippet {{{3

syn region snipSnippet start="^snippet\_s" end="^endsnippet\s*$" contains=snipSnippetHeader fold keepend
syn match snipSnippetHeader "^.*$" nextgroup=snipSnippetBody,snipSnippetFooter skipnl contained contains=snipSnippetHeaderKeyword
syn match snipSnippetHeaderKeyword "^snippet" contained nextgroup=snipSnippetTrigger skipwhite
syn region snipSnippetBody start="\_." end="^\zeendsnippet\s*$" contained contains=snipTabsOnly,snipLeadingSpaces,snipCommand,snipVarExpansion,snipVar,snipVisual nextgroup=snipSnippetFooter
syn match snipSnippetFooter "^endsnippet.*" contained contains=snipSnippetFooterKeyword
syn match snipSnippetFooterKeyword "^endsnippet" contained

" The current parser is a bit lax about parsing. For example, given this:
"   snippet foo"bar"
" it treats `foo"bar"` as the trigger. But with this:
"   snippet foo"bar baz"
" it treats `foo` as the trigger and "bar baz" as the description.
" I think this is an accident. Instead, we'll assume the description must
" be surrounded by spaces. That means we'll treat
"   snippet foo"bar"
" as a trigger `foo"bar"` and
"   snippet foo"bar baz"
" as an attempted multiword snippet `foo"bar baz"` that is invalid.
" NB: UltiSnips parses right-to-left, which Vim doesn't support, so that makes
" the following patterns very complicated.
syn match snipSnippetTrigger "\S\+" contained nextgroup=snipSnippetDocString,snipSnippetTriggerInvalid skipwhite
" We want to match a trailing " as the start of a doc comment, but we also
" want to allow for using " as the delimiter in a multiword/pattern snippet.
" So we have to define this twice, once in the general case that matches a
" trailing " as the doc comment, and once for the case of the multiword
" delimiter using " that has more constraints
syn match snipSnippetTrigger ,\([^"[:space:]]\).\{-}\1\%(\s*$\)\@!\ze\%(\s\+"[^"]*\%("\s\+[^"[:space:]]\+\|"\)\=\)\=\s*$, contained nextgroup=snipSnippetDocString skipwhite
syn match snipSnippetTrigger ,".\{-}"\ze\%(\s\+"\%(\s*\S\)\@=[^"]*\%("\s\+[^"[:space:]]\+\|"\)\=\)\=\s*$, contained nextgroup=snipSnippetDocString skipwhite
syn match snipSnippetTriggerInvalid ,\S\@=.\{-}\S\ze\%(\s\+"[^"]*\%("\s\+[^"[:space:]]\+\s*\|"\s*\)\=\|\s*\)$, contained nextgroup=snipSnippetDocString skipwhite
syn match snipSnippetDocString ,"[^"]*\%("\ze\s*\%(\s[^"[:space:]]\+\s*\)\=\)\=$, contained nextgroup=snipSnippetOptions skipwhite
syn match snipSnippetOptions ,\S\+, contained contains=snipSnippetOptionFlag
syn match snipSnippetOptionFlag ,[biwrts], contained

" Command substitution {{{4

syn region snipCommand keepend matchgroup=snipCommandDelim start="`" skip="\\[{}\\$`]" end="`" contains=snipPythonCommand,snipVimLCommand,snipShellCommand
syn region snipShellCommand start="\ze\_." skip="\\[{}\\$`]" end="\ze`" contained contains=@Shell
syn region snipPythonCommand matchgroup=snipPythonCommandP start="`\@<=!p\_s" skip="\\[{}\\$`]" end="\ze`" contained contains=@Python
syn region snipVimLCommand matchgroup=snipVimLCommandV start="`\@<=!v\_s" skip="\\[{}\\$`]" end="\ze`" contained contains=@Viml

" Variables {{{4

syn match snipVar "\$\d*" contained
syn region snipVisual matchgroup=Define start="\${VISUAL" end="}" contained
syn region snipVarExpansion matchgroup=Define start="\${\d*" end="}" contained contains=snipVar,snipVarExpansion,snipCommand

" global {{{3

" Generic (non-Python) {{{4

syn region snipGlobal start="^global\_s" end="^endglobal\s*$" contains=snipGlobalHeader fold keepend
syn match snipGlobalHeader "^.*$" nextgroup=snipGlobalBody,snipGlobalFooter skipnl contained contains=snipGlobalHeaderKeyword
syn region snipGlobalBody start="\_." end="^\zeendglobal\s*$" contained contains=snipTabsOnly,snipLeadingSpaces nextgroup=snipGlobalFooter

" Python (!p) {{{4

syn region snipGlobal start=,^global\s\+!p\%(\s\+"[^"]*\%("\s\+[^"[:space:]]\+\|"\)\=\)\=\s*$, end=,^endglobal\s*$, contains=snipGlobalPHeader fold keepend
syn match snipGlobalPHeader "^.*$" nextgroup=snipGlobalPBody,snipGlobalFooter skipnl contained contains=snipGlobalHeaderKeyword
syn match snipGlobalHeaderKeyword "^global" contained nextgroup=snipSnippetTrigger skipwhite
syn region snipGlobalPBody start="\_." end="^\zeendglobal\s*$" contained contains=snipTabsOnly,snipLeadingSpaces,@Python nextgroup=snipGlobalFooter

" Common {{{4

syn match snipGlobalFooter "^endglobal.*" contained contains=snipGlobalFooterKeyword
syn match snipGlobalFooterKeyword "^endglobal" contained

" priority {{{3

syn match snipPriority "^priority\%(\s.*\|$\)" contains=snipPriorityKeyword display
syn match snipPriorityKeyword "^priority" contained nextgroup=snipPriorityValue skipwhite display
syn match snipPriorityValue "-\?\d\+" contained display

" Snippt Clearing {{{2

syn match snipClear "^clearsnippets\%(\s.*\|$\)" contains=snipClearKeyword display
syn match snipClearKeyword "^clearsnippets" contained display

" Highlight groups {{{1

hi def link snipComment          Comment
hi def link snipLeadingSpaces    Error
hi def link snipString           String
hi def link snipDocString        String
hi def link snipTabsOnly         Error

hi def link snipKeyword          Keyword

hi def link snipExtendsKeyword   snipKeyword

hi def link snipSnippetHeaderKeyword snipKeyword
hi def link snipSnippetFooterKeyword snipKeyword

hi def link snipSnippetTrigger        Identifier
hi def link snipSnippetTriggerInvalid Error
hi def link snipSnippetDocString      String
hi def link snipSnippetOptionFlag     Special

hi def link snipGlobalHeaderKeyword  snipKeyword
hi def link snipGlobalFooterKeyword  snipKeyword

hi def link snipCommand          Special
hi def link snipCommandDelim     snipCommand
hi def link snipShellCommand     snipCommand
hi def link snipPythonCommand    snipCommand
hi def link snipVimLCommand      snipCommand
hi def link snipPythonCommandP   PreProc
hi def link snipVimLCommandV     PreProc

hi def link snipVar              StorageClass
hi def link snipVarExpansion     Normal
hi def link snipVisual           Normal
hi def link snipSnippet          Normal

hi def link snipPriorityKeyword  Keyword
hi def link snipPriorityValue    Number

hi def link snipClearKeyword     Keyword

" }}}1

let b:current_syntax = "snippets"
