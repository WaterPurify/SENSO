-- 스키마 v6: 말씀 한 잔에 적은 한 줄은 더 이상 저장하지 않는다 (민감정보 최소화).
--   예전에 저장된 한 줄도 지운다. 기분·구절·노트 저장 여부는 그대로 둔다.

UPDATE word_cards SET note = NULL WHERE note IS NOT NULL;
