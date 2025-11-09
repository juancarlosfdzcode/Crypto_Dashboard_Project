SELECT
    coin_id,
    coin_symbol,
    timestamp,
    date,
    price,
    market_cap,
    total_volume,
    extraction_timestamp,
    ROUND(price, 2) AS priceClean,
    {{ toMillions('market_cap') }} AS marketCapMillions,
    {{ toMillions('total_volume') }} AS volumeMillions
FROM {{source('main','market_data')}}  