# Let's Drive Go

Landing page for **Let's Drive Go**, one app for learner drivers, driving instructors and drivers for hire. Built in Staffordshire, heading for the whole UK.

The page explains the app (flexible spot-booking, skill tracking, collaborative credits and integrated insurance), shows plans for learners, instructors and drivers, and collects waitlist sign-ups.

## Files

| File | What it is |
| --- | --- |
| `lets-drive-go.html` | The landing page |
| `images/` | Photos used on the page |
| `server.py` | A small Python server that serves the page and saves waitlist sign-ups |

## Running it locally

It needs Python 3 and nothing else.

```bash
python3 server.py
```

Then open http://127.0.0.1:8765. To use a different port, set the `PORT` environment variable.

## Waitlist sign-ups

The form posts to `/api/waitlist`. The server checks each sign-up (role, name, email and postcode), limits each visitor to 10 sign-ups every 10 minutes, and adds valid ones to `waitlist.csv` next to `server.py`.

`waitlist.csv` contains people's personal details, so it is listed in `.gitignore` and never committed. The server only serves the page and the images folder, so the CSV can't be downloaded from the site.
