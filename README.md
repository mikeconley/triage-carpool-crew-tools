# triage-carpool-crew-tools
A script to find the bugs for triage, and to distribute them evenly to the team to perform triage asynchronously.

# Instructions:

1. After cloning the repository, create a `team.json` file with the following format:

```
{
  "@mconley": {
    "email": "mconley@mozilla.com"
  },
  "@someone": {
    "email": "someoneelse@mozilla.com"
  }
}
```

where each object has some unique identifier as the key (best if that's their Matrix nick), and then the Bugzilla email address as the email. (Note that for PTO or absences, you can also add a "disabled" key to the user object, with the value being a string explaining why)

2. If you don't have [`virtualenv`](https://virtualenv.pypa.io/en/latest/) installed, install it.
3. Create a new virtual environment in the directory, like:

```
$ virtualenv venv
```
4. Activate the virtual environment:

```
$ . venv/bin/activate
```

5. Install the dependencies

```
$ pip install -r requirements.txt
```

6. Run the script:

```
python triage.py
```
