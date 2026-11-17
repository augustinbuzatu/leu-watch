-- Build models in the schema set in dbt_project.yml (e.g. "staging"), matching the
-- layer names, instead of dbt's default "<target schema>_<custom schema>" ("public_staging").
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
