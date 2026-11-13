-- 스키마 v1: 원두·차, 추출 기록, 추천, 취향 테스트 결과

CREATE TABLE beans (
    id            INTEGER PRIMARY KEY,
    kind          TEXT    NOT NULL CHECK (kind IN ('coffee', 'tea')),
    name          TEXT    NOT NULL CHECK (length(trim(name)) > 0),
    roastery      TEXT,
    roast_date    TEXT,                     -- YYYY-MM-DD
    roast_level   TEXT,                     -- 'light' | 'medium' | 'dark' | 'unknown' 등
    photo_path    TEXT,                     -- photos 폴더 기준 파일 이름
    is_sample     INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at    TEXT                      -- 소프트 삭제
);

CREATE TABLE brews (
    id                INTEGER PRIMARY KEY,
    bean_id           INTEGER REFERENCES beans (id),
    bean_snapshot     TEXT    NOT NULL,     -- 기록 당시 원두 정보(JSON)
    brewed_at         TEXT    NOT NULL DEFAULT (datetime('now')),

    -- 추출 전
    desired_flavors   TEXT,                 -- JSON 배열
    hot_or_iced       TEXT    CHECK (hot_or_iced IN ('hot', 'iced')),
    equipment         TEXT,                 -- JSON: {"dripper": ..., "grinder": ...}
    dose_g            REAL    NOT NULL CHECK (dose_g > 0),
    water_g           REAL    NOT NULL CHECK (water_g > 0),
    temp_c            REAL    CHECK (temp_c IS NULL OR temp_c BETWEEN 0 AND 100),
    grind             TEXT,                 -- 기기마다 표기가 달라 문자열
    time_s            INTEGER CHECK (time_s IS NULL OR time_s >= 0),
    ice_g             REAL    CHECK (ice_g IS NULL OR ice_g >= 0),
    notes             TEXT,

    -- 시음 후 (NULL = 아직 입력하지 않음)
    acidity           INTEGER CHECK (acidity      IS NULL OR acidity      BETWEEN 1 AND 5),
    bitterness        INTEGER CHECK (bitterness   IS NULL OR bitterness   BETWEEN 1 AND 5),
    sweetness         INTEGER CHECK (sweetness    IS NULL OR sweetness    BETWEEN 1 AND 5),
    body              INTEGER CHECK (body         IS NULL OR body         BETWEEN 1 AND 5),
    satisfaction      INTEGER CHECK (satisfaction IS NULL OR satisfaction BETWEEN 1 AND 5),
    tasting_notes     TEXT,
    next_wish         TEXT,

    -- 어떤 기록·추천을 보고 만든 기록인지
    based_on_brew_id  INTEGER REFERENCES brews (id) ON DELETE SET NULL,
    based_on_rec_id   INTEGER REFERENCES recommendations (id) ON DELETE SET NULL,

    is_sample         INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_brews_brewed_at ON brews (brewed_at DESC);
CREATE INDEX idx_brews_bean_id ON brews (bean_id);

CREATE TABLE recommendations (
    id                     INTEGER PRIMARY KEY,
    source_brew_id         INTEGER NOT NULL REFERENCES brews (id) ON DELETE CASCADE,
    changed_field          TEXT    NOT NULL,
    from_value             TEXT,
    to_value_or_direction  TEXT    NOT NULL,
    reason                 TEXT    NOT NULL,
    method                 TEXT    NOT NULL DEFAULT 'rule-v1',
    created_at             TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE quiz_results (
    id         INTEGER PRIMARY KEY,
    taken_at   TEXT NOT NULL DEFAULT (datetime('now')),
    answers    TEXT NOT NULL,               -- JSON
    type_code  TEXT NOT NULL
);
