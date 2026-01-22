-- Create Synergy Playtype table
CREATE TABLE IF NOT EXISTS player_synergy_playtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbr TEXT,
    season TEXT DEFAULT '2025-26',
    playtype TEXT NOT NULL,
    games_played INTEGER,
    poss_per_game REAL,
    freq_pct REAL,
    ppp REAL,
    pts_per_game REAL,
    fgm REAL,
    fga REAL,
    fg_pct REAL,
    efg_pct REAL,
    ft_freq_pct REAL,
    tov_freq_pct REAL,
    sf_freq_pct REAL,
    and_one_freq_pct REAL,
    score_freq_pct REAL,
    percentile INTEGER,
    synced_at TEXT,
    UNIQUE(player_name, season, playtype)
);

-- Create Drives table
CREATE TABLE IF NOT EXISTS player_drives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbr TEXT,
    season TEXT DEFAULT '2025-26',
    gp INTEGER,
    min_per_game REAL,
    drives_per_game REAL,
    fgm_per_game REAL,
    fga_per_game REAL,
    fg_pct REAL,
    pts_per_game REAL,
    pts_pct REAL,
    pass_per_game REAL,
    pass_pct REAL,
    ast_per_game REAL,
    ast_pct REAL,
    tov_per_game REAL,
    tov_pct REAL,
    pf_per_game REAL,
    pf_pct REAL,
    synced_at TEXT,
    UNIQUE(player_name, season)
);

-- Create Touches table
CREATE TABLE IF NOT EXISTS player_touches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbr TEXT,
    season TEXT DEFAULT '2025-26',
    gp INTEGER,
    min_per_game REAL,
    pts_per_game REAL,
    touches_per_game REAL,
    front_ct_touches_per_game REAL,
    time_of_poss_per_game REAL,
    avg_sec_per_touch REAL,
    avg_drib_per_touch REAL,
    pts_per_touch REAL,
    elbow_touches_per_game REAL,
    post_ups_per_game REAL,
    paint_touches_per_game REAL,
    pts_per_elbow_touch REAL,
    pts_per_post_touch REAL,
    pts_per_paint_touch REAL,
    synced_at TEXT,
    UNIQUE(player_name, season)
);

-- Create Speed table
CREATE TABLE IF NOT EXISTS player_speed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbr TEXT,
    season TEXT DEFAULT '2025-26',
    gp INTEGER,
    min_per_game REAL,
    dist_feet_per_game REAL,
    dist_miles_per_game REAL,
    dist_miles_off REAL,
    dist_miles_def REAL,
    avg_speed REAL,
    avg_speed_off REAL,
    avg_speed_def REAL,
    synced_at TEXT,
    UNIQUE(player_name, season)
);

-- Create Defense table
CREATE TABLE IF NOT EXISTS player_defense (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbr TEXT,
    season TEXT DEFAULT '2025-26',
    age INTEGER,
    position TEXT,
    gp INTEGER,
    freq_pct REAL,
    dfgm REAL,
    dfga REAL,
    dfg_pct REAL,
    fg_pct REAL,
    diff_pct REAL,
    synced_at TEXT,
    UNIQUE(player_name, season)
);
