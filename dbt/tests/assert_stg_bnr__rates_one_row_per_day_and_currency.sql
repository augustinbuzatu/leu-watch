-- Fails if a currency has more than one rate on the same day.
select
    rate_date,
    currency_code,
    count(*) as row_count
from {{ ref('stg_bnr__rates') }}
group by rate_date, currency_code
having count(*) > 1
