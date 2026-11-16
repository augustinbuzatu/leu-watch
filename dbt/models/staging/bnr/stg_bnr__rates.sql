with

source as (

    select * from {{ source('bnr', 'bnr_rates') }}

),

renamed as (

    select
        rate_date,
        currency as currency_code,
        -- BNR quotes some currencies per 100 units (multiplier = 100, only HUF here).
        -- Every rate is converted to lei for 1 unit of the currency. BNR publishes at most
        -- 4 decimals and the multiplier is at most 100 (a source test checks it), so
        -- 6 decimals keep every converted rate exact.
        cast(rate / coalesce(multiplier, 1) as numeric(18, 6)) as rate_ron,
        loaded_at

    from source

)

select * from renamed
