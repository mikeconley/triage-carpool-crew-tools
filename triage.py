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

TRIAGE_EMAIL_SUBJECT = "Firefox Performance Team - the weekly triage list"

TRIAGE_EMAIL_BODY = """
Hello team,

Here's the weekly triage list.

%s
Thanks,

-Mike
"""

LIST_URL = "https://bugzilla.mozilla.org/rest/bug?include_fields=id,summary,status,creator&keywords=meta&keywords_type=nowords&resolution=---&status_whiteboard=%5Bfxperf%5D&status_whiteboard_type=allwordssubstr"
BUGZILLA_URL = "https://bugzilla.mozilla.org/buglist.cgi?quicksearch=%s"

def main(options):
    logging.debug('Loading team from %s' % options.team_file)
    with open(options.team_file, 'r') as f:
        TEAM = json.load(f)

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

    active_team_keys = list(filter(lambda t: 'disabled' not in TEAM[t], TEAM.keys()))
    active_team_size = len(active_team_keys)

    # Shuffle the keys to make sure the earlier folks in the list don't always
    # get a greater number of bugs to triage.
    distributed = False
    for attempt in range(0, 5):
        logging.info("Attempt %s on getting a good distribution..." % attempt)

        roundrobin_order = list(active_team_keys)
        shuffle(roundrobin_order)

        for victim_key in TEAM:
            TEAM[victim_key]['bugs'] = []

        logging.info("Round robin order: %s" % roundrobin_order)

        bugs_distributed = 0
        for index, bug in enumerate(data['bugs']):
            victim_key = roundrobin_order[index % active_team_size]
            bug = data['bugs'][index]
            if bug['creator'] == TEAM[victim_key]['email']:
                logging.info("Shucks - %s was assigned to bug %s, which they also filed."
                             % (victim_key, bug['id']))
                continue
            TEAM[victim_key]['bugs'].append(bug)
            bugs_distributed = bugs_distributed + 1

        if num_bugs == bugs_distributed:
            distributed = True
            break

    if not distributed:
        logging.error("Couldn't get a good distribution. :(")
        return 1

    logging.info("Distribution completed")
    bug_lists = ""
    for team_member_key in sorted(TEAM.keys(), key=lambda s: s.lower()):
        bugs = TEAM[team_member_key]['bugs']
        logging.info("%s will try to triage %s bug(s)" % (team_member_key, len(bugs)))
        bug_lists += "%s: %s bug(s)\n" % (team_member_key, len(bugs))

        if not len(bugs):
            if 'disabled' in TEAM[team_member_key]:
                bug_lists += "    Away: %s\n\n" % TEAM[team_member_key]['disabled']
            else:
                bug_lists += "    Lucked out this week!\n\n"
            continue
        else:
            bugs_url = BUGZILLA_URL % ("%2C".join(map(lambda b: str(b['id']), bugs)))
            bug_lists += "    List URL: %s\n" % bugs_url

            for bug in sorted(bugs, key=lambda b: b['id']):
                bug_lists += "        Bug %s: %s\n" % (bug['id'], bug['summary'])

        bug_lists += "\n"

    print("\n")
    emails = map(lambda s: TEAM[s]['email'], active_team_keys)
    print("To: %s" % (', '.join(emails)))
    print("\n")
    print("Subject: %s" % TRIAGE_EMAIL_SUBJECT)
    print("\n")
    print(TRIAGE_EMAIL_BODY % bug_lists)

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
    parser.add_argument("--team-file", type=str, dest="team_file",
                        help="Team JSON file", default="team.json")

    options, extra = parser.parse_known_args(sys.argv[1:])

    log_level = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s:  %(message)s", level=log_level)

    sys.exit(main(options))
