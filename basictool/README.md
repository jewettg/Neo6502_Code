# Neo6502 BASIC Tool

```
basictool.py

Based on code written by:
  Paul Robson, paul@robsons.org.uk, Discord: paulscottrobson

This version (a branch of original) maintained by:
  Greg Jewett, jewettg@austin.utexas.edu, Discord: jewettg
  Github Repo:  https://github.com/jewettg/Neo6502_Code
  Combines listbasic and makebasic code bases.

=======================================================================================

This script will:
 * Option for script to de-tokenize a *.bas file
   * Output can be to the console (stdout) or to a file.
   * Has option to include/exclude line numbers in output or export.

 * Option for script to tokenize a basic code text file to a *.bas file
   * File can be specified on command-line or via console (stdin).
   * Output via file (required, parameter)
   * Supports original author's "library", parameter.

=======================================================================================

./basictool.py
usage: basictool.py [-h] {list,make} ...

This tool provides the ability to tokenize a basic code (usually *.bsc) text file or detokenize *.bas (basic tokenized) binary file.

positional arguments:
  {list,make}  sub-command help
    list       Detokenize a *.bas file. Use 'add -h' to list of parameters

				options:
					-h, --help      show this help message and exit
					-n              Flag to specify if line numbers should be generated and included.
					-o OUTPUT_FILE  Output the detokenized basic code to the path/file specified, otherwise stdout
					-f INPUT_FILE   the file to detokenize to text

    make       Tokenize a text file to a *.bas file. Use 'list -h' to list of parameters.

				options:
					-h, --help      show this help message and exit
					-f INPUT_FILE   Specify the path/file of the basic code text file to tokenize, otherwise stdin.
					-o OUTPUT_FILE  Specify the path/file of the tokenized basic code file
					-l              Flag to specify if output should be a library.

options:
  -h, --help   show this help message and exit

Please contact Greg Jewett, via Github issue for support
```
