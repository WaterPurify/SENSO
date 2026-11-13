-- 스키마 v3: 추출 기록 보완
--   next_wish  : 다음에 원하는 변화 (JSON 배열, 예: ["less_bitter"])  ← 기존 칸을 그대로 쓴다
--   next_memo  : 다음에 원하는 맛 자유 메모 (새 칸)
--   brewed_at  : 이제 앱이 기기 현지 시각으로 직접 넣는다 (YYYY-MM-DDTHH:MM)

ALTER TABLE brews ADD COLUMN next_memo TEXT;

CREATE INDEX idx_brews_based_on ON brews (based_on_brew_id);
