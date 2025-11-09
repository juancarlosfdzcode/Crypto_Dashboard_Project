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
    ROUND(market_cap / 1000000.0, 2) AS marketCapMillions,
    ROUND(total_volume / 1000000.0, 2) AS volumeMillions
FROM {{source('main','market_data')}}  