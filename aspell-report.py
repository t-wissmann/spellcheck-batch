#!/usr/bin/env python3
import sys
# import os
import re
import textwrap
import argparse
import subprocess

def parse_aspell_dic_miss_line(line):
    """parse a &-line of aspell, including the &-prefix

    & WRONGWORD SUGGESTION_COUNT WORD_OFFSET_IN_LINE: SUGESSTIONS, ...
    """

    metadata = line.split(':')[0].split(' ')
    res = {
        'word': metadata[1],
        'offset': int(metadata[3]) - 1, # subtract one for the prefixing '^'
        'suggestions': line.split(': ')[1].split(', ')
    }
    return res


def aspell_report_file(lines, aspell_options):
    # see http://aspell.net/man-html/Through-A-Pipe.html
    aspell_full_command = ['aspell', '-a'] + aspell_options
    #print(aspell_full_command)
    proc = subprocess.Popen(aspell_full_command,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            text=True)

    out, _ = proc.communicate(input='\n'.join(['^' + l for l in lines]))
    aspell_lines = out.splitlines()
    line_number = 0
    for aspell_report in aspell_lines:
        if aspell_report == '':
            line_number += 1
            continue
        if aspell_report[0] in ('*', '@'):
            continue
        mistake = parse_aspell_dic_miss_line(aspell_report)
        mistake['line'] = line_number
        yield mistake


def strip_color_escapes(s):
    """strip all color escape sequences from the given string"""
    return re.sub('\033\\[[^m]*m', '', s)


def pretty_print_mistake(lines, mistake, filename):
    prefix = '\033[32m{}\033[36m:\033[33m{}\033[36m:\033[0m' \
             .format(filename, mistake['line'])
    indent =  len(strip_color_escapes(prefix)) + mistake['offset']
    l = lines[mistake['line']]
    print(prefix + l[0:mistake['offset']] +
          '\033[1;31m' +
          l[mistake['offset']:mistake['offset'] + len(mistake['word'])] +
          '\033[0m' + l[mistake['offset'] + len(mistake['word']):])
    print(' ' * indent + '\033[1;31m' + '~' * len(mistake['word']) + '\033[0m')

    sugg_width = 80
    sugg_prefix = '  Suggestions: '
    sugg_cur_width = len(sugg_prefix)
    is_first = True
    print(sugg_prefix, end='')
    for s in mistake['suggestions']:
        if sugg_cur_width + 2 + len(s) > sugg_width and not is_first:
            print(',\n' + ' ' * len(sugg_prefix), end='')
            sugg_cur_width = len(sugg_prefix)
        elif not is_first:
            print(', ', end='')
            sugg_cur_width += 2
        is_first = False
        print(s, end='')
        sugg_cur_width += len(s)
    print('\n')

def check_file(file_handle, file_name, parsed_args):
    lines = file_handle.readlines()
    lines = [l.rstrip('\n\r') for l in lines]
    for report_item in aspell_report_file(lines, parsed_args.backendarg):
        pretty_print_mistake(lines, report_item, file_name)

def main():
    desc = 'Non-interactive spell checking a beautified output'
    epilog = textwrap.dedent("""\
    EXAMPLE:
      - Check all tex files in the current directory:
        aspell-report --files *.tex -- -t --lang=en_GB --variety ize
    """)
    parser = argparse.ArgumentParser(description=desc,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    parser.add_argument('--files', metavar='FILE', type=str, nargs='+',
                        help='Files to check spelling (use stdin if this is empty)')
    parser.add_argument('backendarg', metavar='BACKENDARG', type=str, nargs='*',
                        default=[],
                        help='Arguments passed to the aspell backend')
    args = parser.parse_args()
    files = args.files
    if files is None or files == []:
        check_file(sys.stdin, '<stdin>', args)
    else:
        for fn in files:
            with open(fn, 'r') as file_handle:
                check_file(file_handle, fn, args)
sys.exit(main())
