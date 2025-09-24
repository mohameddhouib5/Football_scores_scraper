import requests
from bs4 import BeautifulSoup

def scrape_matches(date):
    url = f'https://www.yallakora.com/match-center?date={date}'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "lxml")
    matches_details = []

    championships = soup.find_all("div", {"class": "matchCard"})

    for championship in championships:
        championship_title = championship.contents[1].find("h2").text.strip()
        all_matches = championship.find_all("div", {"class": "item"})

        for match in all_matches:
            team_A = match.find("div", {"class": "teamA"}).text.strip()
            team_B = match.find("div", {"class": "teamB"}).text.strip()

            team_A_logo = match.find("div", {"class": "teamA"}).find("img")["src"] if match.find("div", {"class": "teamA"}).find("img") else "N/A"
            team_B_logo = match.find("div", {"class": "teamB"}).find("img")["src"] if match.find("div", {"class": "teamB"}).find("img") else "N/A"

            result_box = match.find("div", {"class": "MResult"})
            score_spans = result_box.find_all("span", {"class": "score"}) if result_box else []
            if score_spans and len(score_spans) == 2:
                score = f"{score_spans[0].text.strip()} - {score_spans[1].text.strip()}"
            else:
                score = "N/A"

            time_span = result_box.find("span", {"class": "time"}) if result_box else None
            match_time = time_span.text.strip() if time_span else "N/A"

            channel_div = match.find("div", {"class": "channel"})
            channel = channel_div.text.strip() if channel_div else "N/A"

            competition_div = match.find("div", {"class": "date"})
            competition = competition_div.text.strip() if competition_div else "N/A"

            matches_details.append({
                "championship": championship_title,
                "competition": competition,
                "team_A": team_A,
                "team_A_logo": team_A_logo,
                "team_B": team_B,
                "team_B_logo": team_B_logo,
                "score": score,
                "match_time": match_time,
                "channel": channel
            })

    return matches_details
