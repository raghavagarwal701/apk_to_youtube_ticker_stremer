from PIL import Image, ImageDraw, ImageFont
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import os
import sys


def extract_cricket_data(json_data):

    batting_team = json_data['currScore']['battingTeamName']
    bowling_team = json_data['currScore']['bowlingTeamName']
    batting_team_data = json_data['currScore']['teamScore'][batting_team]
    on_pitch = batting_team_data['onPitch']
    striker = {
        'name': on_pitch['striker'],
        'runs': on_pitch['strikerScore']['runs'],
        'balls': on_pitch['strikerScore']['balls']
    }
    non_striker = {
        'name': on_pitch['nonStriker'],
        'runs': on_pitch['nonStrikerScore']['runs'],
        'balls': on_pitch['nonStrikerScore']['balls']
    }
    total_runs = batting_team_data['inningScore']
    total_overs = batting_team_data['overs']
    current_bowler = on_pitch['bowlerScore']
    current_over_balls = json_data['currScore']['currOverDetail']['balls']
    
    # Return all extracted data as a dictionary
    return {
        'batting_team': batting_team,
        'bowling_team': bowling_team,
        'striker': striker,
        'non_striker': non_striker,
        'total_runs': total_runs,
        'total_overs': total_overs,
        'current_bowler': current_bowler,
        'current_over_balls': current_over_balls
    }
    
    
    
def generate_image(json_data, match_id):
    score = extract_cricket_data(json_data)
    img = Image.open(('score_image.png'))
    draw = ImageDraw.Draw(img)

    # Load custom font (if available, otherwise default font)
    font_path = ("OpenSans-Regular.ttf")
    default_font_size = 20
    try:
        font = ImageFont.truetype(font_path, default_font_size)
    except IOError:
        font = ImageFont.load_default()

    batting_team_text_width = len(score['batting_team']) * 10
    # Define score details with their specific coordinates and font sizes
    score_elements = [
        {"text": f"{score['batting_team']}", "position": (35, 6), "font_size": 22, "color": "white"},
        {"text": f"{score['bowling_team']}", "position": (35, 45), "font_size": 20, "color": "white"},
        {"text": f"{score['total_runs']}", "position": (35 + batting_team_text_width + 30, 3), "font_size": 25, "color": '#FFCB05'},
        {"text": f"{score['total_overs']} ", "position": (35 + batting_team_text_width + 30 +50, 12), "font_size": 16, "color": "#FFCB05"},
        {"text": f"{score['striker']['name']}:  {score['striker']['runs']}({score['striker']['balls']})", "position": (325, 10), "font_size": 20, "color": "#ACEB6D"},
        {"text": f"{score['non_striker']['name']}:  {score['non_striker']['runs']}({score['non_striker']['balls']})", "position": (325, 45), "font_size": 17, "color": "white"},
        {"text": f"{score['current_bowler']['name']}", "position": (629, 23), "font_size": 20, "color": "#ACEB6D"},
        {"text": f"{score['current_bowler']['ballsDelivered']}", "position": (757, 23), "font_size": 20, "color": "white"},
        {"text": f"balls", "position": (750, 49), "font_size": 12, "color": "white"},
        {"text": f"{score['current_bowler']['runsGiven']}", "position": (802, 23), "font_size": 20, "color": "white"},
        {"text": f"runs", "position": (798, 49), "font_size": 12, "color": "white"},
        {"text": f"{score['current_bowler']['wickets']}", "position": (855, 23), "font_size": 20, "color": "white"},
        {"text": f"wickets", "position": (840, 49), "font_size": 12, "color": "white"},
    ]

    # Loop through score elements and add each to the image
    for element in score_elements:
        # Adjust font size if specified
        font = ImageFont.truetype(font_path, element["font_size"]) if font_path else ImageFont.load_default()
        
        # Add the text to the image at the specified position with the specified color
        draw.text(element["position"], element["text"], font=font, fill=element["color"])

    save_path = f"{match_id}.png"

    if os.path.exists(save_path):
        os.remove(save_path)
        print(f"Existing image {save_path} deleted.")

    img.save(save_path)
    print(f"Image saved as {save_path}")

