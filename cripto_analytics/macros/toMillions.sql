{% macro toMillions(column_name) %}

    ROUND({{ column_name }} / 1000000.0, 2)

{% endmacro %}