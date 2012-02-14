CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id TEXT,
    candidate_id INTEGER
);

CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    vote_code TEXT,
    cached_votes INTEGER DEFAULT 0
);

CREATE UNIQUE INDEX vote_code_index on candidates (vote_code);
CREATE UNIQUE INDEX name_index on candidates (name);

INSERT INTO candidates ("name", "vote_code") VALUES ("Perfect Beauty", "10");
INSERT INTO candidates ("name", "vote_code") VALUES ("Prosperity", "11");
INSERT INTO candidates ("name", "vote_code") VALUES ("Buyosphere", "12");
INSERT INTO candidates ("name", "vote_code") VALUES ("Kismet", "13");
INSERT INTO candidates ("name", "vote_code") VALUES ("Doc pons", "14");
INSERT INTO candidates ("name", "vote_code") VALUES ("Dink life", "15");
INSERT INTO candidates ("name", "vote_code") VALUES ("Evo", "16");
INSERT INTO candidates ("name", "vote_code") VALUES ("Hot seat", "17");
INSERT INTO candidates ("name", "vote_code") VALUES ("Tiny Review", "18");

CREATE TABLE sessions (
    tropo_call_id TEXT,
    caller_network TEXT,
    caller_channel TEXT,
    caller_id TEXT
);
