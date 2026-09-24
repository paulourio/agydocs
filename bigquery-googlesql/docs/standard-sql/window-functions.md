# Window functions

GoogleSQL for BigQuery supports the following
[window functions](window-function-calls.md).

## Function list

| Name | Summary |
|---|---|
| [`CUME_DIST`](numbering_functions.md#cume_dist) | Gets the cumulative distribution (relative position (0,1\]) of each row within a window. For more information, see [Numbering functions](numbering_functions.md). |
| [`DENSE_RANK`](numbering_functions.md#dense_rank) | Gets the dense rank (1-based, no gaps) of each row within a window. For more information, see [Numbering functions](numbering_functions.md). |
| [`FIRST_VALUE`](navigation_functions.md#first_value) | Gets a value for the first row in the current window frame. For more information, see [Navigation functions](navigation_functions.md). |
| [`LAG`](navigation_functions.md#lag) | Gets a value for a preceding row. For more information, see [Navigation functions](navigation_functions.md). |
| [`LAST_VALUE`](navigation_functions.md#last_value) | Gets a value for the last row in the current window frame. For more information, see [Navigation functions](navigation_functions.md). |
| [`LEAD`](navigation_functions.md#lead) | Gets a value for a subsequent row. For more information, see [Navigation functions](navigation_functions.md). |
| [`NTH_VALUE`](navigation_functions.md#nth_value) | Gets a value for the Nth row of the current window frame. For more information, see [Navigation functions](navigation_functions.md). |
| [`NTILE`](numbering_functions.md#ntile) | Gets the quantile bucket number (1-based) of each row within a window. For more information, see [Numbering functions](numbering_functions.md). |
| [`PERCENT_RANK`](numbering_functions.md#percent_rank) | Gets the percentile rank (from 0 to 1) of each row within a window. For more information, see [Numbering functions](numbering_functions.md). |
| [`PERCENTILE_CONT`](navigation_functions.md#percentile_cont) | Computes the specified percentile for a value, using linear interpolation. For more information, see [Navigation functions](navigation_functions.md). |
| [`PERCENTILE_DISC`](navigation_functions.md#percentile_disc) | Computes the specified percentile for a discrete value. For more information, see [Navigation functions](navigation_functions.md). |
| [`RANK`](numbering_functions.md#rank) | Gets the rank (1-based) of each row within a window. For more information, see [Numbering functions](numbering_functions.md). |
| [`ROW_NUMBER`](numbering_functions.md#row_number) | Gets the sequential row number (1-based) of each row within a window. For more information, see [Numbering functions](numbering_functions.md). |
| [`ST_CLUSTERDBSCAN`](geography_functions.md#st_clusterdbscan) | Performs DBSCAN clustering on a group of `GEOGRAPHY` values and produces a 0-based cluster number for this row. For more information, see [Geography functions](geography_functions.md). |