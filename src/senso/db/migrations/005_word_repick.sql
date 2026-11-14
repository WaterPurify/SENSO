-- 스키마 v5: 말씀 카드를 하루에 여러 번 다시 고를 수 있게 한다.
--   word_cards.day 의 UNIQUE 제약을 없앤다 (SQLite는 제약만 지울 수 없어 표를 새로 만든다).
--   그날의 카드는 가장 나중에 고른 것. 앞서 받은 카드도 남아서 말씀 노트에 저장한 것은 그대로다.

CREATE TABLE word_cards_new (
    id          INTEGER PRIMARY KEY,
    day         TEXT    NOT NULL,             -- YYYY-MM-DD (기기 현지 날짜)
    mood        TEXT    NOT NULL,
    verse_ref   TEXT    NOT NULL,
    note        TEXT,
    saved       INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
);

INSERT INTO word_cards_new (id, day, mood, verse_ref, note, saved, created_at)
SELECT id, day, mood, verse_ref, note, saved, created_at FROM word_cards;

DROP TABLE word_cards;
ALTER TABLE word_cards_new RENAME TO word_cards;

CREATE INDEX idx_word_cards_day ON word_cards (day, id);
