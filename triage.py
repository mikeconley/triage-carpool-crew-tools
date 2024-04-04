#!/usr/bin/env python

import argparse
import json
import logging
import random
import requests
import sys

"""
A script to find the bugs for triage, and to distribute them evenly
to the team to perform triage asynchronously.
"""

TRIAGE_EMAIL_SUBJECT = "Front-end Triage Carpool Crew - the triage list"

TRIAGE_EMAIL_BODY = """
Hello team,

Here's the weekly triage list.

%s
Thanks,

-Your friendly triage list generator
"""

REST_URL = "https://bugzilla.mozilla.org/rest/bug?include_fields=id,creator,summary,status&bug_status=UNCONFIRMED&bug_status=NEW&bug_status=ASSIGNED&bug_status=REOPENED&classification=Client%20Software&classification=Developer%20Infrastructure&classification=Components&classification=Server%20Software&classification=Other&f1=OP&f10=component&f11=component&f12=component&f13=component&f14=component&f15=component&f16=component&f17=component&f18=component&f19=product&f2=triage_owner&f20=bug_type&f21=OP&f22=priority&f23=bug_severity&f24=CP&f3=triage_owner&f4=triage_owner&f5=triage_owner&f6=triage_owner&f7=triage_owner&f8=CP&f9=creation_ts&j1=OR&j21=OR&keywords=meta&keywords_type=nowords&o10=notequals&o11=notequals&o12=notequals&o13=notequals&o14=notequals&o15=notequals&o16=notequals&o17=notequals&o18=notequals&o19=notequals&o2=equals&o20=notequals&o22=equals&o23=equals&o3=equals&o4=equals&o5=equals&o6=equals&o7=equals&o9=greaterthan&resolution=---&v10=File%20Handling%20&v11=%20mozscreenshots&v12=Picture-in-Picture%20&v13=Shopping&v14=New%20Tab%20Page&v15=Themes&v16=Theme&v17=Tabbed%20Browser&v18=General&v19=Flowstate&v2=mhowell%40mozilla.com&v20=enhancement&v22=--&v23=--&v3=mconley%40mozilla.com&v4=gijskruitbosch%2Bbugs%40gmail.com&v5=jhirsch%40mozilla.com&v6=cmeador%40mozilla.com&v7=achurchwell%40mozilla.com&v9=2022-01-01"

BUGZILLA_URL = "https://bugzilla.mozilla.org/buglist.cgi?quicksearch=%s"

def main(options):
    logging.debug('Loading team from %s' % options.team_file)
    with open(options.team_file, 'r') as f:
        TEAM = json.load(f)

    logging.debug("Making request to Bugzilla...")

    print("LIST: %s" % (options.rest_url or REST_URL))

    r = requests.get(options.rest_url or REST_URL)
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

    # Randomly distribute bugs to the team, but don't assign a bug's creator to
    # triage it (if the bug's creator is on the team).
    for victim_key in TEAM:
        TEAM[victim_key]['bugs'] = []
    for index, bug in enumerate(data['bugs']):
        possible_triagers = list(filter(lambda t: bug['creator'] != TEAM[t]['email'], active_team_keys))
        # Get the one with the fewest bugs to triage. If there are multiple
        # team members with the same fewest bug count, randomly select one.
        min_bugs = min(len(TEAM[triager_key]['bugs']) for triager_key in possible_triagers)
        min_bug_members = [TEAM[triager_key] for triager_key in possible_triagers if len(TEAM[triager_key]['bugs']) == min_bugs]
        chosen_victim = random.choice(min_bug_members)
        chosen_victim['bugs'].append(bug)

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
    parser.add_argument("--rest-url", type=str, dest="rest_url",
                        help="Optional override for Bugzilla REST URL.")

    options, extra = parser.parse_known_args(sys.argv[1:])

    log_level = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s:  %(message)s", level=log_level)

    sys.exit(main(options))
