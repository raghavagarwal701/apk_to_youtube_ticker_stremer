import requests

def fetch_match_data(match_id):
    url = f"https://qa.gullyball.com/api/v1/cricket/match/{match_id}?getTopPerformers=false"
    response = requests.get(url)
    print(response)
    # print(response.json()["data"]["currScore"]["battingTeamName"])

    if response.status_code == 200:
        match_data = response.json()
    else:
        print(f"Error fetching match data: {response.status_code} - {response.text}")
        return None

    out = {}
    out["batting_team"] = match_data["data"]["currScore"]["battingTeamName"]
    # print("batting team" + out["batting_team"])
    out["bowling_team"] = match_data["data"]["currScore"]["bowlingTeamName"]
    # print("bowling team"+out["bowling_team"])
    out["score"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["inningScore"]
    # print(out["score"])
    out["overs_bowled"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["inningOver"]
    # print(out["overs_bowled"])
    out["batter_one"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["onPitch"]["striker"]
    # print(out["batter_one"])
    out["batter_one_score"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["onPitch"]["strikerScore"]
    # print(out["batter_one_score"])
    out["batter_two"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["onPitch"]["nonStriker"]
    # print(out["batter_two"])
    out["batter_two_score"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["onPitch"]["nonStrikerScore"]
    # print(out["batter_two_score"])
    out["bowler"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["onPitch"]["bowler"]
    # print(out["bowler"])
    out["bowler_figure"] = match_data["data"]["currScore"]["teamScore"][out["batting_team"]]["onPitch"]["bowlerScore"]
    # print(out["bowler_figure"])

    # print(out)
    return out
