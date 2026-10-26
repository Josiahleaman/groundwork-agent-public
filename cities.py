"""
PA cities split into 7 daily batches — one batch per day of the week.
Cycles through all of Pennsylvania over the course of a week.
"""

BATCHES = {
    0: ["Lancaster PA", "York PA", "Harrisburg PA", "Lebanon PA", "Carlisle PA", "Chambersburg PA"],
    1: ["Philadelphia PA", "Norristown PA", "Chester PA", "West Chester PA", "Phoenixville PA", "Coatesville PA"],
    2: ["Pittsburgh PA", "Greensburg PA", "Uniontown PA", "Washington PA", "Butler PA", "New Castle PA"],
    3: ["Allentown PA", "Bethlehem PA", "Easton PA", "Reading PA", "Pottstown PA", "Doylestown PA"],
    4: ["Scranton PA", "Wilkes-Barre PA", "Hazleton PA", "Stroudsburg PA", "Honesdale PA", "Tunkhannock PA"],
    5: ["Erie PA", "Meadville PA", "Sharon PA", "Oil City PA", "Titusville PA", "Bradford PA"],
    6: ["State College PA", "Williamsport PA", "Bloomsburg PA", "Sunbury PA", "Johnstown PA", "DuBois PA"],
}


def get_todays_cities():
    from datetime import date
    day = date.today().weekday()  # 0=Monday, 6=Sunday
    return BATCHES[day]
