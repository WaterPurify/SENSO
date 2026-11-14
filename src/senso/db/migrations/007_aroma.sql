-- 스키마 v7: 시음 후 향(냄새) 평가
--   aroma_intensity : 향의 세기 1~5 (NULL = 미입력)
--   aromas          : 고른 향 계열 키 (JSON 배열, 예: ["floral", "citrus"])
--   aroma_notes     : 고른 세부 향 (JSON 배열, 예: ["자스민", "레몬"])

ALTER TABLE brews ADD COLUMN aroma_intensity INTEGER
    CHECK (aroma_intensity IS NULL OR aroma_intensity BETWEEN 1 AND 5);
ALTER TABLE brews ADD COLUMN aromas TEXT;
ALTER TABLE brews ADD COLUMN aroma_notes TEXT;
