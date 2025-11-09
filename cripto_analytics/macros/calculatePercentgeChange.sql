{% macro calculatePercentageChange(current_value, previous_value) %}

    CASE 
        WHEN {{ previous_value }} IS NULL OR {{ previous_value }} = 0 THEN NULL
        ELSE ROUND((({{ current_value }} - {{ previous_value }}) / {{ previous_value }}) * 100, 2)
    END

{% endmacro %}