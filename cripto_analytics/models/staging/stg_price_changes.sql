WITH price_with_lag AS (
    SELECT
        coin_id,
        coin_symbol,
        date,
        price,
        priceClean,
        marketCapMillions,
        volumeMillions,

        LAG(priceClean, 1) OVER (PARTITION BY coin_id ORDER BY date) AS prev_price_1d,
        LAG(priceClean, 7) OVER (PARTITION BY coin_id ORDER BY date) AS prev_price_7d,
        LAG(priceClean, 30) OVER (PARTITION BY coin_id ORDER BY date) AS prev_price_30d
    FROM {{ ref('stg_market_data') }}
)

SELECT
    coin_id,
    coin_symbol,
    date,
    priceClean,
    marketCapMillions,
    volumeMillions,
    prev_price_1d,
    prev_price_7d,
    prev_price_30d,
    (priceClean - prev_price_1d) AS price_change_1d,
    (priceClean - prev_price_7d) AS price_change_7d,
    (priceClean - prev_price_30d) AS price_change_30d,
    {{ calculatePercentageChange('priceClean', 'prev_price_1d') }} AS pct_change_1d,
    {{ calculatePercentageChange('priceClean', 'prev_price_7d') }} AS pct_change_7d,  
    {{ calculatePercentageChange('priceClean', 'prev_price_30d') }} AS pct_change_30d,
    
    CASE 
        WHEN prev_price_1d IS NOT NULL THEN ABS(priceClean - prev_price_1d) / prev_price_1d 
        ELSE NULL 
    END AS daily_volatility

FROM price_with_lag
