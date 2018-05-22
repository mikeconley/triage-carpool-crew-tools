#!/usr/bin/env python

import argparse
import json
import logging
import requests
import sys

from random import shuffle

"""
A script to find the [fxperf] bugs for triage, and to distribute them evenly
to the team to perform triage asynchronously.
"""

'''
    'florian': {
        'email': 'florian@queze.net',
        'bugs': [],
    },
'''

TEAM = {
    'dthayer': {
        'email': 'dothayer@mozilla.com',
        'bugs': [],
    },

    'felipe': {
        'email': 'felipc@gmail.com',
        'bugs': [],
    },

    'Gijs': {
        'email': 'gijskruitbosch+bugs@gmail.com',
        'bugs': [],
    },

    'mconley': {
        'email': 'mconley@mozilla.com',
        'bugs': [],
    },
}

TRIAGE_EMAIL_SUBJECT = "Firefox Performance Team - the weekly triage list"

TRIAGE_EMAIL_BODY = """
Hello team,

Here's the weekly triage list.

%s
Thanks,

-Mike
"""

LIST_URL = "https://bugzilla.mozilla.org/rest/bug?include_fields=id,summary,status&keywords=meta&keywords_type=nowords&resolution=---&status_whiteboard=%5Bfxperf%5D&status_whiteboard_type=allwordssubstr"
BUGZILLA_URL = "https://bugzilla.mozilla.org/buglist.cgi?quicksearch=%s"

def main(options):
    logging.debug("Making request to Bugzilla...")

    r = requests.get(LIST_URL)
    data = r.json()

    # Do we have enough to distribute evenly?
    if 'bugs' not in data:
        logging.error("Response body made no sense. Bailing out.")
        return 1

    if options.skip_bugs is not None:
        skipped = options.skip_bugs.split(',')
        data['bugs'] = filter(lambda b: str(b['id']) not in skipped, data['bugs'])

    num_bugs = len(data['bugs'])

    if num_bugs == 0:
        logging.info("No bugs for triage! \o/")
        return 0

    logging.info("There are %s bugs to triage" % num_bugs)

    team_size = len(TEAM.keys())

    if num_bugs < len(TEAM.keys()):
        logging.info("Not enough bugs to give to everybody. Randomly choosing some lucky folks.")
        logging.info(data)
        logging.error("HAVEN'T DONE THIS PART YET")
        return 1

    # Shuffle the keys to make sure the earlier folks in the list don't always
    # get a greater number of bugs to triage.
    roundrobin_order = TEAM.keys()
    shuffle(roundrobin_order)

    logging.info("Round robin order: %s" % roundrobin_order)

    for index, bug in enumerate(data['bugs']):
        victim_key = roundrobin_order[index % team_size]
        bug = data['bugs'][index]
        TEAM[victim_key]['bugs'].append(bug)

    logging.info("Distribution completed")
    bug_lists = ""
    for team_member_key in sorted(TEAM.iterkeys(), key=lambda s: s.lower()):
        bugs = TEAM[team_member_key]['bugs']
        logging.info("%s will try to triage %s bug(s)" % (team_member_key, len(bugs)))
        bug_lists += "%s: %s bug(s)\n" % (team_member_key, len(bugs))

        bugs_url = BUGZILLA_URL % ("%2C".join(map(lambda b: str(b['id']), bugs)))
        bug_lists += "    List URL: %s\n" % bugs_url

        for bug in sorted(bugs):
            bug_lists += "        Bug %s: %s\n" % (bug['id'], bug['summary'])

        bug_lists += "\n"

    print "\n"
    emails = map(lambda s: TEAM[s]['email'], TEAM.keys())
    print "To: %s" % (', '.join(emails))
    print "\n"
    print "Subject: %s" % TRIAGE_EMAIL_SUBJECT
    print "\n"
    print TRIAGE_EMAIL_BODY % bug_lists

    # TODO - actually send the email here instead of doing it
    # manually?
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-email", action="store_true", dest="send_email",
                        help="Actually email the team.")
    parser.add_argument("--verbose", action="store_true",
                        help="Print debugging messages to the console.")
    parser.add_argument("--skip-bugs", type=str,
                        help="Bugs to skip.")

    options, extra = parser.parse_known_args(sys.argv[1:])

    log_level = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s:  %(message)s", level=log_level)

    sys.exit(main(options))
