from subprocess import Popen, PIPE

import logging
import re
import sys

import lxml.html


def build_next_call(counter, url, referer=None, agent=None):
    # documentation claims that any argument in the list will be automatically
    # escaped if needed in order to prevent shell escape attacks
    res = ["curl", "-b", "cookies.jar"]

    if agent:
        res += ["-A", agent]

    if referer:
        res += ["-e", referer]

    res += ["-c", "cookies.jar", "-D", "jump%d.header" % counter,
            "-o", "jump%d.body" % counter, url]
    return res


def link_from_header(filename):
    with open(filename, "r") as indata:
        for line in indata:
            tmp = re.match('^\s*Location: (.+)$', line, re.I)
            if tmp:
                return tmp.group(1).strip()
    return None


def link_from_body(filename):
    # lxml.html.parse will return an etree in case of xhtml that lacks the
    # cssselect() method
    dom = lxml.html.document_fromstring(open(filename, "r").read())

    for _ in dom.cssselect('meta'):
        if 'http-equiv' in _.keys():
            k = _.get('http-equiv')

            if k.lower().startswith('location'):
                return _.get('content')
            elif k.lower().startswith('refresh'):
                tmp = re.search('\s(\w+://\S+)', _.get('content'), re.I)
                if tmp:
                    return tmp.group(1)

    # TODO <a> and js
    return None


def manual_input(counter, fallback):
    try:
        res = raw_input('nothing found at jump %d, enter manually: ' % counter)
        return res or fallback
    except KeyboardInterrupt:
        return fallback
    except EOFError:
        return fallback


def trace_link(start_link, referrer=None):
    last_url = None
    referer = referrer
    new_url = start_link
    counter = 1

    while new_url != last_url:
        # never set shell to True or you WILL be pwnd.
        call = build_next_call(counter, new_url, referer=referer)
        cmd = Popen(call, shell=False, stdout=PIPE, stderr=PIPE)
        (out, err) = cmd.communicate()
        result = cmd.returncode

        logging.info("command: %s", call)
        logging.info("step %d: result = %d", counter, result)
        logging.info("stderr: \n%s", err)
        logging.info("stdout: \n%s", out)

        last_url = new_url
        referer = last_url

        new_url = link_from_header("jump%d.header" % counter) or \
                  link_from_body("jump%d.body" % counter) or \
                  manual_input(counter, last_url)

        counter += 1
    print '',


if __name__ == '__main__':
    logging.basicConfig(filename="cmds.log", level=logging.INFO)

    if len(sys.argv) < 2:
        print >> sys.stderr, "Syntax: trace_link.py URL"

    trace_link(sys.argv[1])
