-- 스키마 v8: 책갈피 (나중에 다시 볼 것을 모아 두기)
--   kind  : 'brew' 기록 | 'bean' 원두·차 | 'product' 쇼핑 상품 | 'content' SENSO 소식
--   ref   : 대상의 id 또는 키 (문자열)
--   title : 목록에 보여 줄 이름 (대상이 지워져도 무엇이었는지 알 수 있게)
--   말씀 카드는 이미 '말씀 노트'(word_cards.saved)가 있어 책갈피 탭에서 함께 보여 준다.

CREATE TABLE bookmarks (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('brew', 'bean', 'product', 'content')),
    ref         TEXT NOT NULL,
    title       TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (kind, ref)
);

CREATE INDEX idx_bookmarks_created ON bookmarks (created_at DESC, id DESC);
