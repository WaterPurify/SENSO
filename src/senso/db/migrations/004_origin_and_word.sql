-- 스키마 v4 (사업계획서 v2.5 반영)
--   beans.origin : 산지 (나라·지역, 자유 입력). 국기 표시에 쓴다
--   app_settings : 앱 설정 (예: 말씀 한 잔 켜기/끄기)
--   word_cards   : 오늘의 말씀 한 잔 기록. 하루에 한 장

ALTER TABLE beans ADD COLUMN origin TEXT;

CREATE TABLE app_settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);

CREATE TABLE word_cards (
    id          INTEGER PRIMARY KEY,
    day         TEXT    NOT NULL UNIQUE,      -- YYYY-MM-DD (기기 현지 날짜)
    mood        TEXT    NOT NULL,             -- 기분 키 (예: 'tired')
    verse_ref   TEXT    NOT NULL,             -- 예: '마태복음 11:28'
    note        TEXT,                         -- 사용자가 적은 한 줄 (선택)
    saved       INTEGER NOT NULL DEFAULT 0,   -- 말씀 노트에 저장했는지
    created_at  TEXT    NOT NULL              -- YYYY-MM-DDTHH:MM
);
