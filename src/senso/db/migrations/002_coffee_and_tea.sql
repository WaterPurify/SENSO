-- 스키마 v2: 커피와 차를 함께 담도록 원두 테이블 항목 이름을 정리한다.
--   roastery   -> producer     (커피: 로스터리 / 차: 브랜드·찻집)
--   roast_date -> produced_on  (커피: 로스팅 날짜 / 차: 제조일)
--   tea_type   추가            (차 종류: 녹차, 홍차 ...)

ALTER TABLE beans RENAME COLUMN roastery TO producer;
ALTER TABLE beans RENAME COLUMN roast_date TO produced_on;
ALTER TABLE beans ADD COLUMN tea_type TEXT;

CREATE INDEX idx_beans_kind ON beans (kind, deleted_at);
