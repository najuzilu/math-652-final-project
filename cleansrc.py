from pathlib import Path
import pandas as pd
import numpy as np
from headers_meta import *


def convert_to_minutes(time_str):
    try:
        minutes, seconds = time_str.split(":")
        return int(minutes) + int(seconds) / 60
    except Exception as ex:
        return np.nan
       

def clean_gamelogs(fpath):
    dump_fpath = fpath.parents[1] / "clean"
    dump_fpath.mkdir(parents=True, exist_ok=True)

    dfs = []
    files = [x for x in fpath.iterdir() if x.is_file()]
    for file in files:
        print(f"Iter {file}")
        df = pd.read_csv(file)
        df = df.rename(columns=gamelogs_header)
        # Split game results
        df[["game_results", "results_by_pts"]] = df["game_res"].str.split(expand=True)
        df.results_by_pts = df.results_by_pts.str.strip("()").astype(int)
        df.game_results = df.game_results.str.strip().map(results_map)
        df.age = df.age.str.split("-", expand=True)[0].astype(int)
        df = df.drop(columns=["game_res"])
        dfs.append(df)

    full_df = pd.concat(dfs)

    local_to_numeric = lambda header: pd.to_numeric(np.where(full_df[header].isin(
        ["Did Not Play", "Not With Team", "Did Not Dress",  "DNP", "Inactive", "Player Suspended"]
    ), np.nan, full_df[header]))

    # clean game_started column
    full_df.game_started = full_df.game_started.map(game_started_map)
    # convert date to datetime object
    full_df.date = pd.to_datetime(full_df.date)

    # clean columns
    full_df = full_df.assign(
        year=pd.to_datetime(full_df.date).apply(lambda x: x.year),
        month=pd.to_datetime(full_df.date).apply(lambda x: x.month),
        day=pd.to_datetime(full_df.date).apply(lambda x: x.day),
        team_name=full_df.team.map(team_names),
        opponent_name=full_df.opponent.map(team_names),
        location=np.where(full_df.location.isna(), "home", "away"),
        minutes_played=full_df.minutes_played.apply(convert_to_minutes),
        field_goals=local_to_numeric("field_goals"),
        field_goals_attempts=local_to_numeric("field_goals_attempts"),
        field_goals_pct=local_to_numeric("field_goals_pct"),
        field_goals_3pt=local_to_numeric("field_goals_3pt"),
        field_goals_attempt_3pt=local_to_numeric("field_goals_attempt_3pt"),
        field_goals_pct_3pt=local_to_numeric("field_goals_pct_3pt"),
        free_throws=local_to_numeric("free_throws"),
        free_throws_attempts=local_to_numeric("free_throws_attempts"),
        free_throws_pct=local_to_numeric("free_throws_pct"),
        offensive_rebounds=local_to_numeric("offensive_rebounds"),
        defensive_rebounds=local_to_numeric("defensive_rebounds"),
        total_rebounds=local_to_numeric("total_rebounds"),
        assists=local_to_numeric("assists"),
        steals=local_to_numeric("steals"),
        blocks=local_to_numeric("blocks"),
        turnovers=local_to_numeric("turnovers"),
        personal_fouls=local_to_numeric("personal_fouls"),
        points=local_to_numeric("points"),
        game_score=local_to_numeric("game_score"),
        score_diff=local_to_numeric("score_diff"),
    )
    # drop obs where session is nan
    full_df = full_df[full_df.session.notna()]
    # dump cleaned data
    full_df[[
        'rank', 'season_game', 'player', 'date', 'year',
        'month', 'day',  'age', 'team', 'team_name',  'location', 'opponent', 'opponent_name',
        'game_started', 'minutes_played', 'field_goals', 'field_goals_attempts',
        'field_goals_pct', 'field_goals_3pt', 'field_goals_attempt_3pt',
        'field_goals_pct_3pt', 'free_throws', 'free_throws_attempts',
        'free_throws_pct', 'offensive_rebounds', 'defensive_rebounds',
        'total_rebounds', 'assists', 'steals', 'blocks', 'turnovers',
        'personal_fouls', 'points', 'game_score', 'score_diff', 'session',
        'game_results', 'results_by_pts',  'gamelog_url'
    ]].to_csv(dump_fpath / "gamelogs.csv", index=False)


def clean_players(fpath):
    dump_fpath = fpath.parent / "clean"
    dump_fpath.mkdir(parents=True, exist_ok=True)

    dfs = []
    files = [x for x in fpath.iterdir() if x.is_file()]
    for file in files:
        print(f"Iter {file}")
        df = pd.read_csv(file)
        df = df.rename(columns=player_header)
        dfs.append(df)

    full_df = pd.concat(dfs)
    # convert height
    full_df = full_df.assign(
        position_name=full_df.position.map(position_map),
        height=full_df.height.str.split("-").apply(lambda arr: 12*float(arr[0])+float(arr[1])),
        birth_date=pd.to_datetime(full_df.birth_date),
    )
    full_df[[
        'player_name', 'start_play_period', 'end_play_period', 'position',
        'position_name', 'height', 'weight', 'birth_date', 'college', 
        'player_href']].to_csv(dump_fpath / "players.csv", index=False)


def clean_salary(fpath):
    dump_fpath = fpath.parent / "clean"
    dump_fpath.mkdir(parents=True, exist_ok=True)

    dfs = []
    files = [x for x in fpath.iterdir() if x.is_file()]
    for file in files:
        print(f"Iter {file}")
        df = pd.read_csv(file)
        df = df.rename(columns=salary_header)
        dfs.append(df)

    full_df = pd.concat(dfs)
    # drop salaries '< $Minimum'
    full_df = full_df[full_df.salary != '< $Minimum']
    full_df.salary = full_df.salary.str.replace(
        ',', '').str.replace('$', ''
    ).str.replace("\(TW\)", "").str.strip().astype(float)
    # drop career rows since they can be computed using data from the table
    full_df = full_df[full_df.season != "Career"]
    full_df.season = full_df.season.str.split("-").apply(lambda x: x[0]).astype(int)
    # dump data
    full_df.to_csv(dump_fpath / "salary.csv", index=False)


def merge_sources(gdir, pdir, sdir):
    gamelog_df = pd.read_csv(gdir.parents[1] / "clean" / "gamelogs.csv")
    player_df = pd.read_csv(pdir.parent / "clean" / "players.csv")
    salary_df = pd.read_csv(sdir.parent / "clean" / "salary.csv")
    player_df["player"] = player_df.player_href.str.split("/").str.get(-1).str.split(".").str.get(0)
    merged_df = gamelog_df.merge(player_df, on="player", how="left", indicator=True)
    merged_df = merged_df.drop(columns=["_merge"])
    merged_df = merged_df.rename(columns={"player": "player_id", "session": "season"}).merge(salary_df, on=["season", "player_id"], how="left")

    merged_df[[
        'player_id', 'date', 'year', 'month', 'day','age', 'team', 'team_name', 
        'og_team_name','location', 'opponent', 'opponent_name', 'season', 
        'player_name','start_play_period', 'end_play_period', 'position', 
        'position_name','height', 'weight', 'birth_date', 'college', 'player_href', 
        'gamelog_url','league', 'salary','game_started', 'minutes_played', 'field_goals', 
        'field_goals_attempts','field_goals_pct', 'field_goals_3pt', 'field_goals_attempt_3pt',
        'field_goals_pct_3pt', 'free_throws', 'free_throws_attempts','free_throws_pct', 
        'offensive_rebounds', 'defensive_rebounds','total_rebounds', 'assists', 'steals',
        'blocks', 'turnovers','personal_fouls', 'points', 'game_score', 'score_diff', 
        'game_results', 'results_by_pts']].to_csv(playerdir.parents[1] / "merged_data.csv", index=False)


def compute_season_player_stats(fpath):
    df = pd.read_csv(fpath / "merged_data.csv")

    grouped_df = df.groupby(["player_id", "season", "position", "position_name"]).agg( 
        height=("height", "mean"),
        weight=("weight", "mean"), 
        total_games=("season", "count"), 
        games_started=("game_started", "sum"), 
        total_salary=("salary", "sum"), 
        mean_salary=("salary", "mean"), 
        mean_min_played=("minutes_played", "mean"), 
        mean_field_goals=("field_goals", "mean"),
        mean_field_goals_attempts=("field_goals_attempts", "mean"), 
        mean_field_goals_pct=("field_goals_pct", "mean"),
        mean_field_goals_3pt=("field_goals_3pt", "mean"), 
        mean_field_goals_attempt_3pt=("field_goals_attempt_3pt", "mean"), 
        mean_field_goals_pct_3pt=("field_goals_pct_3pt", "mean"), 
        mean_free_throws=("free_throws", "mean"),
        mean_free_throws_attempts=("free_throws_attempts", "mean"), 
        mean_free_throws_pct=("free_throws_pct", "mean"), 
        mean_offensive_rebounds=("offensive_rebounds", "mean"), 
        mean_defensive_rebounds=("defensive_rebounds", "mean"), 
        mean_total_rebounds=("total_rebounds", "mean"), 
        mean_assists=("assists", "mean"), 
        mean_steals=("steals", "mean"), 
        mean_blocks=("blocks", "mean"), 
        mean_turnovers=("turnovers", "mean"), 
        mean_personal_fouls=("personal_fouls", "mean"),
        mean_points=("points", "mean"),
    ).reset_index()
    grouped_df = grouped_df.assign(
        game_started_share=grouped_df.games_started / grouped_df.total_games
    )
    # for ease of analysis, drop any nan
    # grouped_df = grouped_df.dropna(
    grouped_df.to_csv(fpath / "season_mean_player_stats.csv", index=False)


if __name__ == "__main__":
    datadir = Path(__file__).resolve().parent / "data"
    gamelogdir = datadir / "gamelog" / "src"
    playerdir = datadir / "players" / "src"
    salarydir = datadir / "salary" / "src"
    gamesdir, metadir = gamelogdir / "gamelogs", gamelogdir / "meta"
    # clean_gamelogs(gamesdir)
    # clean_players(playerdir)
    # clean_salary(salarydir)
    # merge_sources(gamesdir, playerdir, salarydir)
    # compute_season_player_stats(datadir)
