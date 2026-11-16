-- Fails for any rate that is zero or negative: an exchange rate is always positive.
select *
from {{ ref('stg_bnr__rates') }}
where rate_ron <= 0
