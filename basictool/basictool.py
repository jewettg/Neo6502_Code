#!/usr/bin/env python
# =======================================================================================
#
# basictool.py
#
# Based on code written by:
#   Paul Robson, paul@robsons.org.uk, Discord: paulscottrobson
#
# This version (a branch of original) maintained by:
#   Greg Jewett, jewettg@austin.utexas.edu, Discord: jewettg
#   Github Repo:  https://github.com/jewettg/Neo6502_Code
#   Combines listbasic and makebasic code bases.
#
# =======================================================================================
#
# This script will:
#  * Option for script to de-tokenize a *.bas file
#    * Output can be to the console (stdout) or to a file.
#    * Has option to include/exclude line numbers in output or export.
#
#  * Option for script to tokenize a basic code text file to a *.bas file
#    * File can be specified on command-line or via console (stdin).
#    * Output via file (required, parameter)
#    * Supports original author's "library", parameter.
#
#
# ---------------------------------------------------------------------------------------
# CHANGE LOG
# 2024-01-02 (PSR) Initial version, original script released.
# 2024-08-29 (GSJ) Branched version, adapted to ensure Python 3 compatibility and
#                  update to a single file.   Add write de-tokenized basic to a file.
#                  Merge listbasic and makebasic code bases into a single tool.
#                  Expanded parameter input and error checking.
#                  Can take stdin and output stdout.
#
# ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
# BEGIN Import modules and dependencies
# ---------------------------------------------------------------------------------------

# Enable Regular Expression support
import re

# The system module for Python, specifically use to get command line arguments.
import sys

# Add support for argument passing, determine flags to know what actions to perform.
import argparse

# The operating system module/library
import os

# Import the object-oriented filesystem paths "pathlib"
import pathlib

# ---------------------------------------------------------------------------------------
# END Import modules and dependencies
# ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
# BEGIN Class Declarations
# ---------------------------------------------------------------------------------------

# CLASS (Detokenizer): Program Listing Class
# ---------------------------------------------------------------------------------------
class ProgramLister:
    def __init__(self,fileName,showLineNumbers):
        self.bin = bytearray(open(fileName,"rb").read(-1))
        self.ts = TokenSet()
        self.dollar = self.ts.getByName("$").getID()
        self.showLineNumbers = showLineNumbers
        self.code_listing = str()

    def list_code(self):
        code = self.bin[0] << 8
        while self.bin[code] != 0:
            self.listLine(code)
            code += self.bin[code]

    def listLine(self,lineStart):
        self.text = "{0} ".format(self.bin[lineStart+1]+self.bin[lineStart+2] * 256) if self.showLineNumbers else ""
        p = lineStart + 3
        while self.bin[p] != self.ts.getByName("!!END").getID():
            p = self.listOneElement(p)
        # print(self.text)
        self.code_listing += self.text + "\n"

    def listOneElement(self,p):
        n = self.bin[p]

        if n >= 0x00 and n < 0x20:
            va = (n << 8)+self.bin[p+1]+5
            p += 2
            name = ""
            while self.bin[va] < 0x80:
                name += chr(self.bin[va])
                va += 1
            name += chr(self.bin[va] & 0x7F)
            self.append(name.lower())

        elif n == self.ts.getByName("!!STR").getID():
            self.append('"'+"".join([chr(self.bin[p+2+c]) for c in range(0,self.bin[p+1])])+'"')
            p = p + self.bin[p+1] + 2

        elif n == self.ts.getByName("!!DEC").getID():
            self.append('.'+"".join([self.decode(self.bin[p+2+c]) for c in range(0,self.bin[p+1])]))
            p = p + self.bin[p+1] + 2

        elif n >= 0x40 and n < 0x80:
            v = 0
            while self.bin[p] >= 0x40 and self.bin[p] < 0x80:
                v = (v << 6) + self.bin[p] - 0x40
                p += 1
            self.append(str(v))

        elif n == self.dollar:
            self.append(" $")
            p += 1
            v = 0
            while self.bin[p] >= 0x40 and self.bin[p] < 0x80:
                v = (v << 6) + self.bin[p] - 0x40
                p += 1
            self.append("{0:x}".format(v))

        elif n >= 0x80 or (n >= 0x20 and n < 0x40):
            p += 1
            if n == self.ts.getByName("!!SH1").getID():
                n = self.bin[p] + 0x100
                p += 1
            if n == self.ts.getByName("!!SH2").getID():
                n = self.bin[p] + 0x200
                p += 1
            s = self.ts.getByID(n).getName()
            self.append(s)

        else:
            self.text += "[{0:02x}]".format(self.bin[p])
            p += 1

        return p

    def append(self,s):
        if self.text != "" and self.type(self.text[-1]) == self.type(s[0]):
            self.text += " "
        self.text += s

    def type(self,c):
        c = c.upper()
        if c != ' ':
            c = 'I' if (c >= '0' and c <= '9') or (c >= 'A' and c <= 'Z') or c == '_' else 'N'
        return c

    def decode(self,d):
        return "{0}{1}".format("" if (d & 240) == 240 else d >> 4,"" if (d & 15) == 15 else (d & 15))


# CLASS (Detokenizer): Class representing an individual token
# ---------------------------------------------------------------------------------------
class Token(object):
    def __init__(self,tokenID,token):
        self.modifier = ""
        if token != ":" and token.find(":") >= 0:
            self.modifier = token[token.find(":")+1:]
            token = token[:token.find(":")]
        self.token = token
        self.tokenID = tokenID
    #
    def getName(self):
        return self.token
    def getID(self):
        return self.tokenID
    def getModifier(self):
        return self.modifier



# CLASS (Detokenizer): Class representing all the tokens
# ---------------------------------------------------------------------------------------
class TokenSet(object):
    def __init__(self):
        self.create()

    def getByID(self,id):
        return self.idToToken[id] if id in self.idToToken else None
    def getByName(self,name):
        name = name.strip().lower()
        return self.nameToToken[name] if name in self.nameToToken else None

    def getRange(self,start):
        assert start in self.idToToken
        ids = []
        while start in self.idToToken:
            ids.append(self.idToToken[start])
            start += 1
        return ids

    def getAllTokenNames(self):
        return [x for x in self.nameToToken.keys() if x != ""]

    def add(self,start,tokens,padSize = None):
        self.nextToken = start if start is not None else self.nextToken
        start = self.nextToken
        for s in tokens.upper().strip().split():
            self.addToken(self.nextToken,s)
            self.nextToken += 1
        if padSize is not None:
            while self.nextToken < start + padSize:
                self.addToken(self.nextToken,"")
                self.nextToken += 1

    def addToken(self,tokenID,tokenText):
        tokenText = tokenText.strip().lower()
        assert tokenID not in self.idToToken,"Duplicate "+tokenText
        if tokenText != "":
            assert tokenText not in self.nameToToken,"Duplicate "+tokenText
        token = Token(tokenID,tokenText)
        self.idToToken[tokenID] = token
        self.nameToToken[token.getName()] = token

    def create(self):
        self.nextToken = None
        self.idToToken = {}
        self.nameToToken = {}
        #
        #        Binary tokens between $20 and $3F
        #
        self.add(0x20,"""
             +:3    -:3     *:4     /:4        >>:4    <<:4    %:4     \\:4
             &:1    |:1        ^:1        >:2        >=:2    <:2        <=:2    <>:2
             =:2
            """)
        #
        #        Unary tokens from $80-$B0
        #
        self.add(0x80,"""
            !!STR     $         (        RAND(    RND(    JOYPAD(    INT(    TIME(    EVENT(
            INKEY$(    ASC(    CHR$(    POINT(     LEN(      ABS(      SGN(     HIT(    SPOINT(
            MID$(    LEFT$(     RIGHT$(    TRUE    FALSE    INSTR(    MOUSE(    !!UN6    !!UN7
            KEY(    PEEK(    DEEK(    ALLOC(    MAX(     MIN(
            """,48)
        #
        #        Structure tokens
        #
        self.add(None,"""
            WHILE:+    WEND:-        IF:+    ENDIF:-    DO:+    LOOP:-         REPEAT:+     UNTIL:-
            PROC:+     ENDPROC:-    FOR:+     NEXT:-     CASE:+     ENDCASE:-     !!UN1:+     THEN:-
             """,16)
        #
        #        Keyword tokens (major)
        #
        self.add(None,"""
            !!END     !!SH1    !!SH2    !!DEC     TO         LET     PRINT    INPUT
            SYS     EXIT    ,         ;         :         '         )        READ
            DATA     ELSE    WHEN    DOWNTO     POKE    DOKE     LOCAL    CALL
            #         .         LINE     RECT     MOVE     PLOT     ELLIPSE    TEXT
            IMAGE     SPRITE     FROM     [        ]         @         TILEDRAW REF
            """)
        #
        #        Keyword tokens (minor)
        #
        self.add(0x180,"""
            CLEAR     NEW     RUN     STOP     END     ASSERT     LIST     SAVE
            LOAD    CAT     GOSUB     GOTO    RETURN     RESTORE    DIM        FKEY
            CLS     INK        FRAME    SOLID    BY         WHO     PALETTE DRAW
            HIDE     FLIP     SOUND     SFX     ANCHOR    GLOAD    DEFCHR  LEFT
            RIGHT     FORWARD    TURTLE     CLOSE     TILEMAP PENUP   PENDOWN FAST
            HOME     LOCALE     CURSOR     RENUMBER DELETE EDIT      MON     OLD
            ON         ERROR     PIN     OUTPUT    WAIT     IWRITE     ANALOG  ISEND
            SSEND     IRECEIVE SRECEIVE ITRANSMIT STRANSMIT OPEN LIBRARY
            USEND     URECEIVE UTRANSMIT UCONFIG MOS     MOUSE     SHOW     NOISE
            """)
        #
        #        Keyword tokens (assembler)
        #
        self.add(0x280,"""
            ADC    AND    ASL    BCC    BCS    BEQ    BIT    BMI    BNE    BPL    BRA    BRK    BVC    BVS
            CLC    CLD    CLI    CLV    CMP    CPX    CPY    DEC    DEX    DEY    EOR    INC    INX    INY
            JMP    JSR    LDA    LDX    LDY    LSR    NOP    ORA    PHA    PHP    PHX    PHY    PLA    PLP
            PLX    PLY    ROL    ROR    RTI    RTS    SBC    SEC    SED    SEI    STA    STX    STY    STZ
            TAX    TAY    TRB    TSB    TSX    TXA    TXS    TYA

        """,0x50)
        #
        #        Additional Unary functions, less popular
        #
        self.add(0x2D0,"""
            ATAN2( EOF( !!UU2 !!UU3 !!UU4 !!UU5 !!UU6 !!UU7
            !!UU8 !!UU9 !!UU10 !!UU11 !!UU12 !!UU13 !!UU14 !!UU15
            SIN(     COS(    TAN(    ATAN(     LOG(      EXP(      VAL(     STR$(
            ISVAL(     SQR(     PAGE     SPRITEX( SPRITEY( NOTES( HIMEM     VBLANKS(
            ERR     ERL        PIN(     IREAD(      ANALOG(  JOYCOUNT(  UPPER$(
            IDEVICE( SPC(     TAB(     UHASDATA( MOS(     HAVEMOUSE( LOWER$( POW(
            EXISTS(
        """)


# CLASS (Tokenizer):  Identifier storage class
# ---------------------------------------------------------------------------------------

class IdentifierStore(object):
	def __init__(self):
		self.store = [ 0x1 ] 																# one page.
		self.identifiers = {}
	#
	def render(self):
		reqLength = self.store[0] * 256  													# Actual size
		render = [x for x in self.store] 													# make a copy
		while len(render) < reqLength:  													# Pad out with zeor.
			render.append(0)
		return render
	#
	def get(self,name):
		name = name.upper()
		return self.identifiers[name] if name in self.identifiers else None
	#
	def add(self,name):
		name = name.upper()
		bAddress = len(self.store)
		assert name not in self.identifiers
		self.identifiers[name] = len(self.store)+1 											# Points to data, offset 1 in record.
		isString = name.endswith("$") or name.endswith("$(") 								# Work out type byte
		isArray = name.endswith("(")
		self.store.append(len(name)+6)														# Offset byte
		self.store += [0,0,0,0] 															# default value
		ctrl = 0x80 if isString else 0x00
		ctrl = ctrl + 0x10 if isArray else ctrl
		self.store.append(ctrl) 															# control byte.
		b = [ord(x) for x in name] 															# work out name
		b[-1] |= 0x80
		self.store += b																		# name
		aAddress = len(self.store)
		if (bAddress & 0x80) == 0 and (aAddress & 0x80) != 0:  								# creating crossed the middle of the page
			self.store[0] += 1 																# Another page.

		return self
	#
	def dump(self):
		data = self.render()
		pos = 1
		while data[pos] != 0:
			p1 = pos + 6
			name = ""
			done = False
			while not done:
				name += chr(data[p1] & 0x7F)
				done = (data[p1] & 0x80) != 0
				p1 += 1
			print("Record ${0:04x} : ${1:02x} {2}{3}".format(pos,data[pos+5],name.lower(),"" if (data[pos+1] & 0xC0) == 0 else "$"))
			pos += data[pos]


# CLASS (Tokenizer):  Tokeniser worker class
# ---------------------------------------------------------------------------------------
class Tokeniser(object):
	def __init__(self,identStore):
		self.ts = TokenSet()
		self.iStore = identStore
	#
	def tokenise(self,s):
		s = s.strip()
		self.code = []
		while s != "" and not s.startswith("//"):
			s = self.tokeniseOne(s).strip()
		return self.code
	#
	def tokeniseOne(self,s):
		#
		#		Numbers, compiled in base 64
		#
		if s[0] >= "0" and s[0] <= "9":
			m = re.match("(\\d+)\\s*(.*)$",s)
			self.renderConstant(int(m.group(1)))
			s = m.group(2)
			m = re.match('\\.(\\d+)\\s*(.*)',s)
			if m is not None:
				digits = ([int(x) for x in m.group(1)] + [0xF])
				digits = digits if len(digits) % 2 == 0 else digits + [0xF]
				self.code.append(self.getTokenID("!!dec"))
				self.code.append(len(digits) >> 1)
				while len(digits) > 0:
					self.code.append(digits[0]*16+digits[1])
					digits = digits[2:]
				return m.group(2)
			return s
		#
		#		Hexadecimal numbers also in base 64
		#
		if s[0] == '$':
			m = re.match("\\$([0-9A-Fa-f]+)\\s*(.*)$",s)
			self.code.append(self.getTokenID("$"))
			self.renderConstant(int(m.group(1),16))
			return m.group(2)
		#
		#		Quoted string : [!!str] [length] [characters]
		#
		if s[0] == '"':
			m = re.match('\\"(.*?)\\"\\s*(.*)',s)
			self.code.append(self.getTokenID("!!str"))
			self.code.append(len(m.group(1)))
			self.code += [ord(c) for c in m.group(1)]
			return m.group(2)
		#
		#		Decimals [!!dec] [length] [digits packed in BCD, ending in $F, max of 8 digits]
		#
		#
		#		Comment
		#
		if s[0] == "'":
			s = s[1:].strip()
			self.code.append(self.getTokenID("'"))
			if s != "":
				s = s.replace('"','')
				self.code.append(self.getTokenID("!!str"))
				self.code.append(len(s))
				self.code += [ord(c) for c in s]
			return ""
		#
		#		Identifier or Token
		#
		if s[0].upper() >= "A" and s[0].upper() <= "Z":
			m = re.match("^([A-Za-z0-9\\_\\.]+\\$?\\(?)\\s*(.*)$",s)
			t = self.ts.getByName(m.group(1))
			if t is not None:
				id = t.getID()
				if id >= 0x100:
					self.code.append(self.getTokenID("!!sh"+str(id >> 8)))
				self.code.append(id & 0xFF)
			else:
				if self.iStore.get(m.group(1)) is None:
					self.iStore.add(m.group(1))
				id = self.iStore.get(m.group(1))
				self.code.append(id >> 8)
				self.code.append(id & 0xFF)
			return m.group(2)
		#
		#		Punctuation
		#
		if len(s) >= 2:
			id = self.ts.getByName(s[:2])
			if id is not None:
				self.code.append(id.getID())
				return s[2:]
		#
		id = self.ts.getByName(s[0])
		assert id is not None
		self.code.append(id.getID())
		return s[1:]
	#
	def getTokenID(self,name):
		return self.ts.getByName(name).getID()
	#
	def renderConstant(self,n):
		if n >= 64:
			self.renderConstant(n >> 6)
		self.code.append(0x40|(n & 0x3F))
	#
	def test(self,s):
		code = self.tokenise(s)
		print("{0}\n\t{1}".format(s,",".join(["{0:02x}".format(n) for n in code])))



# CLASS (Tokenizer):  Program Builder Class
# ---------------------------------------------------------------------------------------
class Program:
	def __init__(self):
		self.nextLine = 100
		self.lineStep = 10
		self.code = []
		self.store = IdentifierStore()
		self.store.add("A")
		self.store.add("O")
		self.store.add("P")
		self.store.add("X")
		self.store.add("Y")
		self.ts = TokenSet()
		self.tw = Tokeniser(self.store)
		self.identifiers = {}
		self.libraryMode = False
	#
	#		Add the contents of the file, stripping // comments
	#
	def addFile(self,fileName):
		for s in open(fileName).readlines():
			s = s.strip()
			if s.startswith("#"):
				self.command(s[1:])
				s = ""
			s = s.strip()
			s = self.processIdentifiers(s)
			if s != "":
				number = None
				if s[0] >= "0" and s[0] <= "9":
					m = re.match("^(\\d+)(.*)$",s)
					number = int(m.group(1))
					s = m.group(2)
				self.addLine(number,s)
	#
	#		Handle #commands.
	#
	def command(self,c):
		if c.startswith("define"):
			c = c[6:].strip()
			n = c.find(" ")
			self.identifiers[c[:n]] = c[n+1:].strip()
		elif c == "library":
			self.libraryMode = True
		elif c == "nolibrary":
			self.libraryMode = False
			self.nextLine = 1000
		else:
			assert False,"Bad #command '#"+c+"'"

	#
	#		Process identifiers, making define substitutions.
	#
	def processIdentifiers(self,s):
		src = re.split("([A-Za-z][A-Za-z0-9\\._]*)",s)
		for i in range(0,len(src)):
			if src[i] in self.identifiers:
				src[i] = self.identifiers[src[i]]
		return "".join(src)
	#
	#		Add a line with an optional line number
	#
	def addLine(self,number = None,text = ""):
		if text.strip() != "":
			if number is not None:
				self.nextLine = number
			lineNo = 0 if self.libraryMode else self.nextLine
			#print(lineNo,text)
			line = [0,lineNo & 0xFF,lineNo >> 8]
			line += self.tw.tokenise(text)
			line.append(self.ts.getByName("!!end").getID())
			line[0] = len(line)
			#print(line)
			self.code += line
			self.nextLine += self.lineStep

		return self
	#
	#		Make program a library
	#
	def makelibrary(self):
		p = 0
		while p != len(self.code):
			self.code[p+1] = 0
			self.code[p+2] = 0
			p += self.code[p]
	#
	#		Save the resulting tokenised code.
	#
	def render(self,fileName):
		h = open(fileName,"wb")
		h.write(bytes(self.store.render()+self.code+[0]))
		h.close()


# ---------------------------------------------------------------------------------------
# END Class Declarations
# ---------------------------------------------------------------------------------------



# ---------------------------------------------------------------------------------------
# BEGIN Functions Declarations
# ---------------------------------------------------------------------------------------

def process_parameters():
    scriptDesc = ("This tool provides the ability to tokenize a basic code (usually *.bsc) text file"
                  " or detokenize *.bas (basic tokenized) binary file." )

    aParser = argparse.ArgumentParser(  description = scriptDesc,
                                        epilog="Please contact Greg Jewett, via Github issue for support",
                                        add_help = True,
                                        allow_abbrev=False)

    subParsers = aParser.add_subparsers(help='sub-command help',
                                        required = True,
                                        dest='cmd')

    # ---------------------------------------------------------------------------------------
    # BEGIN SUB-COMMAND: list (detokenize a *.bas file)
    # ---------------------------------------------------------------------------------------
    addParser = subParsers.add_parser("list", help="Detokenize a *.bas file.  Use 'add -h' to list of parameters")

    # PARAMETER:  Specify if line numbers should be generated and included.
    # ------------------------------------------------------------------------
    addParser.add_argument( "-n",
                            action = "store_true",
                            dest = "linenumbers",
                            help = "Flag to specify if line numbers should be generated and included.",
                            required = False)

    # PARAMETER:  output_file (empty string if not specified)
    # ------------------------------------------------------------------------
    addParser.add_argument( "-o",
                            action = "store",
                            type = str,
                            dest = "output_file",
                            default = "",
                            help = "Output the detokenized basic code to the path/file specified, otherwise stdout",
                            required = False)

    # PARAMETER:  input_file (file to detokenize)
    # ------------------------------------------------------------------------
    addParser.add_argument( "-f",
                            action = "store",
                            type = str,
                            dest = "input_file",
                            help = "the file to detokenize to text",
                            required = True)



    # ---------------------------------------------------------------------------------------
    # END SUB-COMMAND: list (detokenize a *.bas file)
    # ---------------------------------------------------------------------------------------


    # ---------------------------------------------------------------------------------------
    # BEGIN SUB-COMMAND: make (tokenize a text file)
    # ---------------------------------------------------------------------------------------
    listParser = subParsers.add_parser("make", help="Tokenize a text file to a *.bas file. Use 'list -h' to list of parameters.")

    # PARAMETER:  input_file (empty string if not specified)
    # ------------------------------------------------------------------------
    listParser.add_argument( "-f",
                            action = "store",
                            type = str,
                            dest = "input_file",
                            default = "",
                            help = "Specify the path/file of the basic code text file to tokenize, otherwise stdin.",
                            required = False)

    # PARAMETER:  input_file (empty string if not specified)
    # ------------------------------------------------------------------------
    listParser.add_argument( "-o",
                            action = "store",
                            type = str,
                            dest = "output_file",
                            help = "Specify the path/file of the tokenized basic code file",
                            required = True)

    # PARAMETER:  Make Library option ()
    # ------------------------------------------------------------------------
    listParser.add_argument( "-l",
                            action = "store_true",
                            dest = "makelibrary",
                            help = "Flag to specify if output should be a library.",
                            required = False)

    # ---------------------------------------------------------------------------------------
    # END SUB-COMMAND: make (tokenize a text file)
    # ---------------------------------------------------------------------------------------


    # Check to see if any parameters were provided, as there are some that are required.
    # If none provided, then output the help section.
    # ------------------------------------------------------------------------
    if len(sys.argv) < 2:
        aParser.print_help()
        sys.exit(1)

    # return the parameters and the boolean if all validation passed.
    return vars(aParser.parse_args())

# ---------------------------------------------------------------------------------------
# END Functions Declarations
# ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
# BEGIN Script
# ---------------------------------------------------------------------------------------

if __name__ == "__main__":
    # =======================================================================================
    # CHECK PYTHON VERSION
    # Error out for any Python version earlier than minimum supported version.
    # =======================================================================================
    minVer = (3,8,8)
    curVer = sys.version_info[0:]
    if curVer < minVer:
        print("Current Python version: {}.{}.{}".format(*curVer+(0,0,)))
        print("ABORT: Expect Python version {}.{}.{}".format(*minVer+(0,0,))+" or better required!")
        sys.exit(1)

    # ts = TokenSet()
    # print(ts.getRange(0x80))
    # print(ts.getRange(0x180))
    # print(ts.getRange(0x20))
    # print(ts.getRange(0x280))
    # print(ts.nameToToken.keys())
    # print(ts.getByName("!!str"))
    # print(ts.nameToToken.keys())

    optParams = process_parameters()

    theCommand = str(optParams.get("cmd"))
    linenumbers = str(optParams.get("linenumbers"))
    output_file = str(optParams.get("output_file"))
    input_file = str(optParams.get("input_file"))
    makelibrary = str(optParams.get("makelibrary"))

    print("\n\nNeoBASIC Tool")
    print("---------------------------------------------")
    print("Operation: %s" % theCommand)
    if theCommand == "list":
        print("Line Numbers: %s" % linenumbers)
        print("Output: %s" % (output_file if output_file else "Console (stdout)"))
        print("Input: %s" % (input_file if input_file else "Console (stdout)"))
        print("---------------------------------------------\n")
        # program_listing = ProgramLister(input_file, linenumbers).list_code()
        program_listing = ProgramLister(input_file, linenumbers)
        program_listing.list_code()

        if not output_file:
            print(program_listing.code_listing)
        else:
            with open(output_file, mode='w') as file_handle:
                file_handle.write(program_listing.code_listing)

        print("\n---------------------------------------------")
        print("Finished.")

    if theCommand == "make":
        print("Input: %s" % (input_file if input_file else "Console (stdin)"))
        print("Output: %s" % (output_file))
        print("---------------------------------------------\n")
        tokenize_program = Program()

        if makelibrary:
            tokenize_program.makelibrary()

        if not input_file:
            console_input = sys.stdin.read()
            with open("temp.txt", mode='w') as file_handle:
                file_handle.write(console_input)
            tokenize_program.addFile("temp.txt")
            tokenize_program.render(output_file)
            # Clean-up after myself, and delete the temporary file.
            os.remove("temp.txt")
        else:
            tokenize_program.addFile(input_file)
            tokenize_program.render(output_file)

        print("\n---------------------------------------------")
        print("Finished.")



# output = "basic.tok"
# prog = Program()
# for f in sys.argv[1:]:
# 	if f.startswith("-o"):
# 		output = f[2:]
# 	elif f == "library":
# 		prog.makelibrary()
# 	else:
# 		prog.addFile(f)
# prog.render(output)

# ---------------------------------------------------------------------------------------
# END Script
# ---------------------------------------------------------------------------------------
