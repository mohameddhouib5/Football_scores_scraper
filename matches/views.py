import json
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import re
from django.shortcuts import render
from .scraper import scrape_matches

# Configure logging
logger = logging.getLogger(__name__)

def home(request):
    date_str = request.GET.get("date", "").strip()
    matches = []
    error = ""

    # Log current time for reference
    now = datetime.now()
    logger.info("Current server time: %s", now)

    # Fetch matches from scraper
    if date_str:
        try:
            matches = scrape_matches(date_str) or []
            logger.info("Raw scraped matches: %s", matches)
        except Exception as e:
            error = f"Failed to fetch matches: {str(e)}"
            logger.error("Scraper error: %s", error)
            matches = []

    def normalize(m, request_date_str):
        """Normalize match data and determine status"""
        now = datetime.now()

        # Parse scraped match data
        if isinstance(m, dict):
            base = {
                "league_name": m.get("league_name") or m.get("championship") or m.get("league") or "Unknown",
                "is_live": bool(m.get("is_live")) or (str(m.get("status", "")).lower() == "live"),
                "status": m.get("status", ""),
                "kickoff_time": m.get("kickoff_time") or m.get("match_time") or m.get("time") or "",
                "home_name": m.get("home_name") or m.get("team_A") or m.get("home") or m.get("title") or "",
                "home_score": str(m.get("home_score") or m.get("score_home") or m.get("score") or "").strip(),
                "home_logo_url": m.get("home_logo_url") or m.get("team_A_logo") or m.get("logo_A") or "",
                "away_name": m.get("away_name") or m.get("team_B") or m.get("away") or "",
                "away_score": str(m.get("away_score") or m.get("score_away") or "").strip(),
                "away_logo_url": m.get("away_logo_url") or m.get("team_B_logo") or m.get("logo_B") or "",
                "minute": m.get("minute", ""),
                "period": m.get("period", ""),
                "venue": m.get("venue", ""),
                "channel": m.get("channel") or m.get("tv") or m.get("broadcast") or "N/A",
            }
        else:
            # Fallback for malformed data
            title = str(m)
            parts = title.split(" ")
            home = parts[0].strip() if parts else title
            away = parts[1].strip() if len(parts) > 1 else ""
            base = {
                "league_name": "Unknown",
                "is_live": False,
                "status": "",
                "kickoff_time": "",
                "home_name": home,
                "home_score": "",
                "home_logo_url": "",
                "away_name": away,
                "away_score": "",
                "away_logo_url": "",
                "minute": "",
                "period": "",
                "venue": "",
                "channel": "N/A",
            }

        # Log raw match data
        logger.info("Processing match: %s", base)

        # Split combined score if necessary
        if base["home_score"] and not base["away_score"]:
            score_match = re.match(r"(\d+)\s*-\s*(\d+)", base["home_score"])
            if score_match:
                base["home_score"], base["away_score"] = score_match.groups()
                logger.info("Split score: home_score=%s, away_score=%s", base["home_score"], base["away_score"])
            else:
                logger.warning("Failed to split score: %s", base["home_score"])

        # Determine if scores are valid
        has_score = (
            base["home_score"] and base["away_score"] and
            base["home_score"] != " " and base["away_score"] != " "
        )
        logger.info("Has valid scores: %s (home_score: '%s', away_score: '%s')",
                    has_score, base["home_score"], base["away_score"])

        # Parse kickoff_time and request date
        match_date_time = None
        if base["kickoff_time"] and request_date_str:
            try:
                date_parts = request_date_str.split("/")
                if len(date_parts) == 3:
                    month, day, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                    time_parts = base["kickoff_time"].split(":")
                    if len(time_parts) == 2:
                        hours, minutes = int(time_parts[0]), int(time_parts[1])
                        match_date_time = datetime(year, month, day, hours, minutes)
                        logger.info("Parsed match_date_time: %s", match_date_time)
                    else:
                        logger.warning("Invalid kickoff_time format: %s", base["kickoff_time"])
                else:
                    logger.warning("Invalid date format: %s", request_date_str)
            except (ValueError, IndexError) as e:
                logger.warning("Failed to parse kickoff_time '%s' or date '%s': %s",
                              base["kickoff_time"], request_date_str, str(e))

        # Determine status
        if base["is_live"] or base["status"].lower() == "live":
            base["status_display"] = "Live"
            base["status_class"] = "status-live"
        elif base["status"].lower() in ["ft", "finished"] or (
            has_score and match_date_time and match_date_time < now - timedelta(minutes=90)
        ):
            base["status_display"] = "Full Time"
            base["status_class"] = "status-finished"
        elif match_date_time and match_date_time > now:
            base["status_display"] = "Upcoming"
            base["status_class"] = "status-upcoming"
        elif has_score and match_date_time and match_date_time <= now:
            base["status_display"] = "Live"
            base["status_class"] = "status-live"
        else:
            base["status_display"] = "Upcoming"
            base["status_class"] = "status-upcoming"

        base["score_class"] = base["status_class"].replace("status-", "score-")
        logger.info("Assigned status: %s (class: %s)", base["status_display"], base["status_class"])

        return base

    # Normalize matches
    normalized = [normalize(m, date_str) for m in matches]
    logger.info("Normalized matches: %s", normalized)

    # Group matches by league
    grouped = defaultdict(list)
    for nm in normalized:
        grouped[nm.get("league_name") or "Unknown"].append(nm)

    # Serialize matches for debugging
    try:
        raw_matches_json = json.dumps(matches, default=str, ensure_ascii=False, indent=2)
    except Exception as e:
        raw_matches_json = str(matches)
        logger.error("Failed to serialize matches: %s", str(e))

    context = {
        "date": date_str,
        "matches_by_league": dict(grouped),
        "raw_matches_json": raw_matches_json,
        "error": error,
    }

    return render(request, "matches/home.html", context)