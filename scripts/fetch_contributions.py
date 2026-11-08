#!/usr/bin/env python3
"""
Scrape real daily contribution counts from GitHub's public, unauthenticated
contributions endpoint (the same fragment the profile page itself uses) and
write data/contributions.json with the raw days plus derived stats
(current streak, longest streak, best day, monthly totals).

No token, no auth, no GraphQL -- just the public HTML GitHub already serves.
Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_PROFILE_USER", "theaadishjain")
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")


def fetch_days():
    resp = requests.get(URL, headers={"User-Agent": "profile-readme-bot/1.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)

    # one pass over the tooltips instead of a full-document search per cell
    tooltips = {tt.get("for"): tt.get_text(strip=True) for tt in soup.find_all("tool-tip")}

    days = []
    unparsed = 0
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        text = tooltips.get(td.get("id"), "")
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            if m:
                count = int(m.group(1))
            else:
                unparsed += 1
                count = 0
        # GitHub's own color bucket (0-4) for this day -- using it verbatim is
        # what makes our graph shade exactly like the one on the profile page.
        try:
            level = int(td.get("data-level", ""))
        except ValueError:
            level = None
        days.append({"date": date, "count": count, "level": level})

    # if GitHub's markup changes, tooltips stop matching and every day would
    # silently read as 0 -- refuse to continue rather than overwrite real data.
    if days and unparsed > len(days) * 0.05:
        print(f"could not parse {unparsed}/{len(days)} day tooltips -- "
              "github markup may have changed", file=sys.stderr)
        sys.exit(1)

    days.sort(key=lambda d: d["date"])

    # month labels exactly as GitHub lays them out: each spans N week-columns
    months = []
    for td in soup.select("td.ContributionCalendar-label[colspan]"):
        label = td.find("span", attrs={"aria-hidden": "true"})
        try:
            span = int(td["colspan"])
        except ValueError:
            continue
        months.append({"label": label.get_text(strip=True) if label else "", "span": span})

    # the headline number GitHub prints above the graph
    github_total = None
    h2 = soup.find(id="js-contribution-activity-description")
    if h2:
        m = re.search(r"([\d,]+)\s+contribution", h2.get_text(" ", strip=True))
        if m:
            github_total = int(m.group(1).replace(",", ""))

    return days, months, github_total


def load_existing():
    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def compute_current_streak(days):
    if not days:
        return 0, None, None
    idx = len(days) - 1
    if days[idx]["count"] == 0:
        idx -= 1  # today isn't over yet -- don't break the streak on it
    if idx < 0:
        return 0, None, None
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    if streak == 0:
        return 0, None, None
    return streak, days[start_idx]["date"], days[end_idx]["date"]


def compute_longest_streak(days):
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
    return longest, longest_start, longest_end


def build_data(days, months=None, github_total=None):
    if not days:
        print("no contribution days found -- cannot build data", file=sys.stderr)
        sys.exit(1)

    total = github_total if github_total is not None else sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"])
    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    monthly = {}
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "month_labels": months or [],
        "days": days,
    }


if __name__ == "__main__":
    days, months, github_total = fetch_days()
    existing = load_existing()

    if (existing and existing.get("days") == days
            and existing.get("month_labels") == months
            and existing.get("total_contributions") == (github_total or sum(d["count"] for d in days))):
        # nothing changed -- leave the file untouched so no commit is made
        print(f"{OUT_PATH} already up to date; not rewriting")
        sys.exit(0)

    data = build_data(days, months, github_total)
    if existing and existing.get("total_contributions", 0) > 0 and data["total_contributions"] == 0:
        print("scrape returned 0 contributions but previous data was non-zero -- "
              "refusing to overwrite (likely a scrape failure)", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT_PATH}: {data['total_contributions']} contributions, "
          f"current streak {data['current_streak']['length']}, "
          f"longest streak {data['longest_streak']['length']}")
